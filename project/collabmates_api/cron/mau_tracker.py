from togther.models import ModelUtilities, CommunityBillingDates, ActiveUserMonthlyData, ActiveUser
from collabmates_api.sdk.models import SdkClient
from collabmates_api.raw_queries import get_users_meta_info
from external_services.logging.logging_wrapper import LoggingWrapper

from django.conf import settings
from datetime import date, datetime
from dateutil import relativedelta
from celery import shared_task
import json
import boto3
import time

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


def getUUIDOfUsers(community_id, users_list):
    return get_users_meta_info(community_id, users_list)


def getFilteredCloudwatchLogs():

    client = boto3.client('logs',
                         region_name=settings.AWS_REGION,
                         aws_access_key_id=settings.CLOUDWATCH_AWS_ACCESS_KEY_ID,
                         aws_secret_access_key=settings.CLOUDWATCH_AWS_SECRET_ACCESS_KEY)

    query = f"""
    fields  log_processed.text.request.headers.api_key,
            log_processed.text.request.headers.sdk_source,
            log_processed.text.request.body.user_unique_id,
            log_processed.text.request.headers.x_member_id,
            log_processed.text.request.query.uuid
    | filter kubernetes.container_name = "{settings.CLOUDWATCH_KUBERNETES_CONTAINER_NAME}"
    | filter log_processed.text.request.absolute_uri like "api/sdk/initiate"
        or log_processed.text.request.absolute_uri like "api/chatroom/fetch"
        or log_processed.text.request.absolute_uri like "api/v2/fetch_chatroom"
    | sort @timestamp desc
    """

    try:
        response = client.start_query(
            logGroupName=settings.CLOUDWATCH_LOG_GROUP,
            startTime=int((datetime.now() - relativedelta.relativedelta(days=1)).timestamp()),
            endTime=int(datetime.now().timestamp()),
            queryString=query
        )

        # polling loop to wait for results
        while True:
            logs = client.get_query_results(queryId=response['queryId'])
            status = logs['status']
            
            if status in ['Complete', 'Failed', 'Cancelled']:
                break
                
            time.sleep(1)  # Wait 1 second before checking again

        if status in ['Failed', 'Cancelled']:
            return []
        
        # Transform the field names in the response
        if 'results' in logs:
            for result in logs['results']:
                for field in result:
                    if field['field'] == 'log_processed.text.request.headers.api_key':
                        field['field'] = 'api_key'
                    elif field['field'] == 'log_processed.text.request.headers.sdk_source':
                        field['field'] = 'sdk_source'
                    elif field['field'] == 'log_processed.text.request.body.user_unique_id':
                        field['field'] = 'user_unique_id'
                    elif field['field'] == 'log_processed.text.request.headers.x_member_id':
                        field['field'] = 'x_member_id'
                    elif field['field'] == 'log_processed.text.request.query.uuid':
                        field['field'] = 'uuid'

            return logs['results']
        else:
            return []

    except Exception as e:
        error_logger.error(f"Error querying CloudWatch Logs: {str(e)}")
        return []

def getUserListFromCloudWatchData(cloudwatch_data, api_key, sdk_source):
    """Extract user IDs from CloudWatch Logs data"""
    users_list = set()

    if not cloudwatch_data:
        return users_list

    # Group fields by result entry using @ptr as identifier
    for result in cloudwatch_data:
        entry_api_key = None
        entry_sdk_source = None
        
        # First check if this entry matches our api_key and sdk_source
        for field in result:
            if field['field'] == 'api_key':
                entry_api_key = field['value']
            elif field['field'] == 'sdk_source':
                entry_sdk_source = field['value']
        
        # Skip if entry doesn't match our filters
        if entry_api_key != api_key or entry_sdk_source != sdk_source:
            continue

        # Extract user IDs from various fields
        for field in result:
            if field['field'] in ['x_member_id', 'uuid', 'user_unique_id']:
                users_list.add(field['value'])

    return users_list


def updateUniqueUsersOfACommunityBillingEntry(billingRecord, cloudwatchData):
    
    # Fetch sdk client record to fetch api key
    try:
        sdk_client = SdkClient.objects.get(community=billingRecord.community)
    except Exception as e:
        error_logger.error(f"Error fetching SdkClient for community {billingRecord.community}: {str(e)}")
        return

    # If no record exists for given community, break the flow
    if not sdk_client:
        return

    # Fetch unique user Ids from above fetched cloudwatch data
    users_list = getUserListFromCloudWatchData(cloudwatchData, sdk_client.api_key, billingRecord.sdk)

    if not users_list:
        # Logging user list received
        info_logger.info("""MAU Tracker Cloudwatch Data: {}[{}] - No Data Found """.format(billingRecord.community.name,
                                                                                          billingRecord.sdk))
        return

    # Logging user list received
    info_logger.info("""MAU Tracker Cloudwatch Data: {}[{}] ({}) - {} """.format(billingRecord.community.name,
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
    cloudwatchData = getFilteredCloudwatchLogs()

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
        updateUniqueUsersOfACommunityBillingEntry(billingRecord, cloudwatchData)

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
