from togther.models import ModelUtilities, CommunityBillingDates, ActiveUserMonthlyData, ActiveUser
from collabmates_api.sdk.models import SdkClient
from collabmates_api.raw_queries import get_users_meta_info
from external_services.logging.logging_wrapper import LoggingWrapper

from django.conf import settings
from datetime import date
from dateutil import relativedelta
import requests

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


# Method to get Data from Coralogix API
def getCoralogixData(filters):
    hits = []
    fetch_again = True

    # First Scroll API Call
    response = requests.post(url="https://coralogix-esapi.coralogix.com:9443/*/_search",
                             params={
                                 'scroll': '5m'
                             },
                             json={
                                 'size': 10000,
                                 'query': filters
                             },
                             headers={
                                 'token': settings.CORALOGIX_LOGGER.get('PRIVATE_API_KEY'),
                                 'Content-type': 'application/json'
                             })

    # If request succeeds
    if response.status_code == 200:
        scroll_id = response.json()['_scroll_id']

        # Fetch hits value from response
        if response.json()['hits'] and response.json()['hits']['hits']:
            hits.append(response.json()['hits']['hits'])
        else:
            fetch_again = False

        # Loop till all the response is fetched
        while fetch_again:
            # Consecutive Scroll API Calls
            response2 = requests.post(url="https://coralogix-esapi.coralogix.com:9443/_search/scroll",
                                      json={
                                          'scroll': '5m',
                                          'scroll_id': scroll_id,
                                          'size': 10000,
                                          'query': filters
                                      },
                                      headers={
                                          'token': 'f246d6f2-2fe3-4444-a963-689330ea689c',
                                          'Content-type': 'application/json'
                                      })

            # If request succeeds
            if response2.status_code == 200:
                scroll_id = response2.json()['_scroll_id']

                # Fetch hits value from response
                if response2.json()['hits'] and response2.json()['hits']['hits']:
                    hits.extend(response2.json()['hits']['hits'])
                else:
                    fetch_again = False

            else:
                fetch_again = False

    else:
        error_logger.error('error while making request on coralogix: {}'.format(response.json()))

    return hits

def getUUIDOfUsers(community_id, users_list):
    user_int_list = []

    # Segregate integer user ids from user list
    for user in users_list:
        if any([isinstance(user, int), isinstance(user, str) and user.isdigit()]):
            user_int_list.append(user)

    return get_users_meta_info(community_id, users_list, user_int_list)

def getUserListFromCoralogixData(coralogixData):
    users_list = set()

    # Fetch user ids from the coralogix hits data
    if coralogixData:
        for entry in coralogixData[0]:
            if entry['_source'] and entry['_source']['request']:
                request_entry = entry['_source']['request']
                if request_entry.get('headers') and request_entry['headers'].get('x_member_id'):
                    users_list.add(request_entry['headers']['x_member_id'])

                if request_entry['body']:
                    if request_entry['body'].get('user_unique_id'):
                        users_list.add(request_entry['body']['user_unique_id'])

                    if request_entry['body'].get('chatroom_participants'):
                        for participant in request_entry['body']['chatroom_participants']:
                            users_list.add(participant)

                    if request_entry['body'].get('secret_chatroom_participants'):
                        for participant in request_entry['body']['secret_chatroom_participants']:
                            users_list.add(participant)

    return users_list

def updateUniqueUsersOfACommunityBillingEntry(billingRecord):
    # Fetch application Name based on environment
    applicationName = 'LikeMinds_Beta' if settings.IS_BETA else 'LikeMinds_Prod'

    # Fetch sdk client record to fetch api key
    sdk_client = SdkClient.objects.get(community=billingRecord.community)

    # If no record exists for given community, break the flow
    if not sdk_client:
        return

    api_key = sdk_client.api_key
    additional_filters = {}

    # Filter to fetch data based on applicationName, api_key and timestamp
    filters = {
        'bool': {
            'must': [
                {
                    'match_phrase': {
                        'coralogix.metadata.applicationName': settings.CORALOGIX_LOGGER.get('APPLICATION_NAME')
                    }
                },
                {
                    'match_phrase': {
                        'request.headers.api_key': api_key
                    }
                },
                {
                    'range': {
                        'coralogix.timestamp': {
                            'gte': 'now-24h',
                            'lt': 'now'
                        }
                    }
                }
            ]
        }
    }

    # Filter update if sdk is for 'feed'
    if billingRecord.sdk == 'feed':
        additional_filters: dict = {
            'must': [
                {
                    'match_phrase': {
                        'request.absolute_uri': 'api/sdk/initiate',
                    }
                },
                {
                    'match_phrase': {
                        'request.method': 'POST'
                    }
                },
                {
                    'term': {
                        'request.headers.sdk_source': billingRecord.sdk
                    }
                }
            ]
        }

    # Filter update if sdk is for 'chat'
    if billingRecord.sdk == 'chat':
        additional_filters: dict = {
            'must': [
                {
                    'bool': {
                        'should': [
                            {
                                'bool': {
                                    'must': [
                                        {
                                            'match_phrase': {
                                                'request.absolute_uri': 'api/sdk/initiate',
                                            }
                                        },
                                        {
                                            'match_phrase': {
                                                'request.method': 'POST'
                                            }
                                        }
                                    ]
                                }
                            },
                            {
                                'bool': {
                                    'must': [
                                        {
                                            'match_phrase': {
                                                'request.absolute_uri': 'api/community/member',
                                            }
                                        },
                                        {
                                            'match_phrase': {
                                                'request.method': 'POST'
                                            }
                                        }
                                    ]
                                }
                            },
                            {
                                'bool': {
                                    'must': [
                                        {
                                            'match_phrase': {
                                                'request.absolute_uri': 'api/chatroom/add',
                                            }
                                        },
                                        {
                                            'match_phrase': {
                                                'request.method': 'POST'
                                            }
                                        }
                                    ]
                                }
                            },
                            {
                                'bool': {
                                    'must': [
                                        {
                                            'match_phrase': {
                                                'request.absolute_uri': 'api/chatroom/secret/add',
                                            }
                                        },
                                        {
                                            'match_phrase': {
                                                'request.method': 'POST'
                                            }
                                        }
                                    ]
                                }
                            },
                        ]
                    }
                },
                {
                    'bool': {
                       'should': [
                           {
                               'bool': {
                                   'must': [
                                       {
                                           'match_phrase': {
                                               'request.headers.sdk_source.keyword': ''
                                           }
                                       },
                                   ],
                                   'must_not': [
                                       {
                                           'match_phrase': {
                                               'request.headers.platform_code': 'fl'
                                           }
                                       },
                                   ]
                               }
                           },
                           {
                               'match_phrase': {
                                   'request.headers.sdk_source': billingRecord.sdk
                               }
                           }
                       ]
                    }
                }
            ]
        }

    # Update major filters with additional filters
    filters['bool']['must'].extend(additional_filters.get('must'))

    # Fetch coralogix data for above generated filters
    coralogixData = getCoralogixData(filters)

    # Fetch unique user Ids from above fetched coralogix data
    users_list = getUserListFromCoralogixData(coralogixData)

    # Fetch LM UUIDs for all the above fetched user IDs
    final_user_list = getUUIDOfUsers(billingRecord.community.id, users_list)

    # Create or Update the records for each active user UUID for each billing record
    if final_user_list:
        for user in final_user_list:
            ModelUtilities.update_or_create_model(ActiveUser, {'billing': billingRecord,
                                                               'uuid': user.get('user_unique_id')}, {})

def updateUniqueUsersDataOfACommunityInActiveMonthlyData(billingRecord, today):
    # Fetch active user IDs for a specific billing record
    activeUsers = ModelUtilities.get_model_filter(ActiveUser, {'billing': billingRecord}).value_list('uuid', flat=True)

    # Create monthly active user data for a billing record
    ModelUtilities.update_or_create_model(ActiveUserMonthlyData,
                                          {'billing': billingRecord,
                                           'start_date': today-relativedelta.relativedelta(months=1),
                                           'end_date': today},
                                          {'mau_count': len(activeUsers),
                                           'user_list': str(activeUsers)})

def track():
    # Fetch all the billing records for which MAU needs to be computed
    billingRecords = ModelUtilities.get_model_filter(CommunityBillingDates, {})
    today = date.today()

    for billingRecord in billingRecords:
        # Update Unique Active Users of a Billing record for the day
        updateUniqueUsersOfACommunityBillingEntry(billingRecord)

        # If New month started for a billing record
        if today.strftime("%d") == str(billingRecord.start_date):
            # Fetch all the unique users for a billing record in a month and Create a MonthlyActiveUsers Record
            updateUniqueUsersDataOfACommunityInActiveMonthlyData(billingRecord, today)

            # If record exists for the current date in MonthlyActiveUsers
            monthlyDataRecord = ModelUtilities.get_model_filter(ActiveUserMonthlyData, {'billing': billingRecord,
                                                                                        'end_date': today})
            if monthlyDataRecord:
                # Delete all the ActiveUser records for that billing record
                ModelUtilities.delete_record_in_model(ActiveUser, {'billing': billingRecord})
