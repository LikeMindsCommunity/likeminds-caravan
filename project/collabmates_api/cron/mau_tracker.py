from togther.models import ModelUtilities, CommunityBillingDates, ActiveUserMonthlyData, ActiveUser
from collabmates_api.sdk.models import SdkClient
from collabmates_api.raw_queries import get_users_meta_info
from external_services.logging.logging_wrapper import LoggingWrapper

from django.conf import settings
from datetime import date, datetime, timezone
from dateutil import relativedelta
from celery import shared_task
import json

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


def getUUIDOfUsers(community_id, users_list):
    return get_users_meta_info(community_id, users_list)


def getFilteredLogs():
    try:
        # Initialize Azure Log Analytics client
        from azure.monitor.query import LogsQueryClient
        from azure.identity import ClientSecretCredential

        credential = ClientSecretCredential(
            tenant_id=settings.AZURE_TENANT_ID,
            client_id=settings.AZURE_CLIENT_ID,
            client_secret=settings.AZURE_CLIENT_SECRET
        )

        client = LogsQueryClient(credential)

        # KQL query to fetch relevant logs
        query = """
        ContainerLogV2
        | where ContainerName == "{container_name}"
        | where LogMessage.text.request.absolute_uri has "api/sdk/initiate" 
            or LogMessage.text.request.absolute_uri has "api/chatroom/fetch" 
            or LogMessage.text.request.absolute_uri has "api/v2/fetch_chatroom"
        | project LogMessage.text.request.headers.api_key,
            LogMessage.text.request.headers.sdk_source,
            LogMessage.text.request.body.user_unique_id,
            LogMessage.text.request.headers.x_member_id,
            LogMessage.text.request.query.uuid
        """.format(container_name=settings.AZURE_KUBERNETES_CONTAINER_NAME)

        # Execute the query
        response = client.query_workspace(
            workspace_id=settings.AZURE_LOG_ANALYTICS_WORKSPACE_ID,
            query=query,
            timespan=(datetime.now(timezone.utc) - relativedelta.relativedelta(days=1), datetime.now(timezone.utc))
        )

        # Process and transform the results
        results = []
        if response and response.tables:
            for table in response.tables:
                for row in table.rows:
                    try:
                        results.append(row._row_dict)
                    except Exception:
                        continue

        info_logger.info(f"Retrieved {len(results)} logs from Azure Log Analytics")
        return results

    except Exception as e:
        error_logger.error(f"Error querying Azure Log Analytics: {str(e)}")
        return []


def getUserListFromAzureLogs(logs_data, api_key, sdk_source):
    """Extract user IDs from Azure Log Analytics data"""
    users_list = set()

    if not logs_data:
        return users_list

    for log_entry in logs_data:
        # Check if this entry matches our api_key and sdk_source
        entry_api_key = log_entry.get('LogMessage_text_request_headers_api_key')
        entry_sdk_source = log_entry.get('LogMessage_text_request_headers_sdk_source')
        
        # Skip if entry doesn't match our filters
        if entry_api_key != api_key or entry_sdk_source != sdk_source:
            continue

        # Extract user IDs from various fields
        user_id = log_entry.get('LogMessage_text_request_body_user_unique_id')
        member_id = log_entry.get('LogMessage_text_request_headers_x_member_id')
        uuid = log_entry.get('LogMessage_text_request_query_uuid')

        if user_id:
            users_list.add(user_id)
        if member_id:
            users_list.add(member_id)
        if uuid:
            users_list.add(uuid)

    return users_list


def updateUniqueUsersOfACommunityBillingEntry(billingRecord, logsData):
    # Fetch sdk client record to fetch api key
    try:
        sdk_client = SdkClient.objects.get(community=billingRecord.community)
    except Exception as e:
        error_logger.error(f"Error fetching SdkClient for community {billingRecord.community}: {str(e)}")
        return

    # If no record exists for given community, break the flow
    if not sdk_client:
        return

    # Fetch unique user Ids from above fetched logs data
    users_list = getUserListFromAzureLogs(logsData, sdk_client.api_key, billingRecord.sdk)

    if not users_list:
        # Logging user list received
        info_logger.info("""MAU Tracker Azure Logs Data: {}[{}] - No Data Found """.format(billingRecord.community.name,
                                                                                          billingRecord.sdk))
        return

    # Logging user list received
    info_logger.info("""MAU Tracker Azure Logs Data: {}[{}] ({}) - {} """.format(billingRecord.community.name,
                                                                                billingRecord.sdk,
                                                                                len(users_list),
                                                                                users_list))

    # Fetch LM UUIDs for all the above fetched user IDs
    final_user_list = getUUIDOfUsers(billingRecord.community.id, users_list)

    # Logging user list converted by our system
    info_logger.info("""MAU Tracker System Generated Data: {}[{}] ({}) - {}""".format(billingRecord.community.name,
                                                                                      billingRecord.sdk,
                                                                                      len(final_user_list),
                                                                                      final_user_list))

    # Create or Update the records for each active user UUID for each billing record
    if final_user_list:
        for user in final_user_list:
            ModelUtilities.update_or_create_model(ActiveUser, {'billing': billingRecord,
                                                               'uuid': user.get('user_unique_id')}, {})


def updateUniqueUsersDataOfACommunityInActiveMonthlyData(billingRecord, today):
    # Fetch active user IDs for a specific billing record
    activeUsers = list(ModelUtilities.get_model_filter(ActiveUser,
                                                       {'billing': billingRecord}).values_list('uuid', flat=True))

    # Create monthly active user data for a billing record
    ModelUtilities.update_or_create_model(ActiveUserMonthlyData,
                                          {'billing': billingRecord,
                                           'start_date': (today-relativedelta.relativedelta(months=1)).strftime("%s"),
                                           'end_date': today.strftime("%s")},
                                          {'mau_count': len(activeUsers),
                                           'users_list': json.dumps(activeUsers)})


@shared_task
def track():
    # Logging process stage
    info_logger.info("""MAU Tracker Log: - {}""".format("MAU Tracking Started"))

    # Fetch all the billing records for which MAU needs to be computed
    billingRecords = ModelUtilities.get_model_filter(CommunityBillingDates, {})
    today = date.today()

    # Premptively fetch all logs
    logsData = getFilteredLogs()
    
    for billingRecord in billingRecords:
        # Logging process stage
        info_logger.info("""MAU Tracker Log: {}[{}] - {}""".format(billingRecord.community.name,
                                                                   billingRecord.sdk,
                                                                   "Tracking Process Started"))
        
        # If record exists for the current date in MonthlyActiveUsers
        monthlyDataRecord = ModelUtilities.get_model_filter(ActiveUserMonthlyData,
                                                            {'billing': billingRecord,
                                                             'start_date': (today-relativedelta.relativedelta(months=1)).strftime("%s"),
                                                             'end_date': today.strftime("%s")})
        if monthlyDataRecord:
            # Alrready data exists do nothing and continue
            info_logger.info("""MAU Tracker Log: {}[{}] - {}""".format(billingRecord.community.name,
                                                                       billingRecord.sdk,
                                                                       "ActiveUserMonthlyData Already Exists with this start date, end date - Skipping Process"))
            
            continue

        # Update Unique Active Users of a Billing record for the day
        updateUniqueUsersOfACommunityBillingEntry(billingRecord, logsData)

        # Logging process stage
        info_logger.info("""MAU Tracker Log: {}[{}] - {}""".format(billingRecord.community.name,
                                                                   billingRecord.sdk,
                                                                   "Users Updated in Active Users"))

        # If New month started for a billing record
        if int(today.strftime("%d")) == billingRecord.start_date:
            # Logging process stage
            info_logger.info("""MAU Tracker Log: {}[{}] - {}""".format(billingRecord.community.name,
                                                                       billingRecord.sdk,
                                                                       "Data Aggregation Started"))

            # Fetch all the unique users for a billing record in a month and Create a MonthlyActiveUsers Record
            updateUniqueUsersDataOfACommunityInActiveMonthlyData(billingRecord, today)

            # Logging process stage
            info_logger.info("""MAU Tracker Log: {}[{}] - {}""".format(billingRecord.community.name,
                                                                       billingRecord.sdk,
                                                                       "Data Updated in Monthly Data Users"))

            # If record exists for the current date in MonthlyActiveUsers
            monthlyDataRecord = ModelUtilities.get_model_filter(ActiveUserMonthlyData,
                                                                {'billing': billingRecord,
                                                                 'end_date': today.strftime("%s")})
            if monthlyDataRecord:
                # Logging process stage
                info_logger.info("""MAU Tracker Log: {}[{}] - {}""".format(billingRecord.community.name,
                                                                           billingRecord.sdk,
                                                                           "Active Users Data Deletion Started"))

                # Delete all the ActiveUser records for that billing record
                ModelUtilities.delete_record_in_model(ActiveUser, {'billing': billingRecord})

        # Logging process stage
        info_logger.info("""MAU Tracker Log: {}[{}] - {}""".format(billingRecord.community.name,
                                                                   billingRecord.sdk,
                                                                   "Tracking Process Completed"))

    # Logging process stage
    info_logger.info("""MAU Tracker Log: - {}""".format("MAU Tracking Completed"))
