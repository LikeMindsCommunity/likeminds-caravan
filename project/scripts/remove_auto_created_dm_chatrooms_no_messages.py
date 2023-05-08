import time

from collabmates_api.sdk.models import (SdkClient)
from togther.models import (ModelUtilities, Collabcard, card_answers, collabcardState, conversationEngage)
from utility.states import (card_types, conversation_states)

api_key = '5bf0d9d9-5864-4863-b2fb-364298b612a2'


def remove_auto_created_dm_chatrooms_no_messages():
    filter_dict = {
        'is_deleted': False
    }

    if api_key:
        filter_dict['api_key'] = api_key

    sdk_communities_filter = ModelUtilities.get_model_filter(SdkClient, filter_dict)

    count = sdk_communities_filter.count()

    print('Total communities count', count)

    for sdk_community_instance in sdk_communities_filter:
        print('Communities left', count)

        filter_dict = {
            'community': sdk_community_instance.community,
            'state': conversation_states.ANSWER,
            'card__is_private': True,
            'card__type': card_types.CARD_DIRECT_MESSAGE
        }

        card_ids_with_user_messages = list(ModelUtilities.get_model_filter(card_answers, filter_dict).values_list(
            'card_id', flat=True))

        # Deleting conversation engage
        ModelUtilities.get_model_filter(conversationEngage, {'community': sdk_community_instance.community,
                                                             'card__is_private': True,
                                                             'card__type': card_types.CARD_DIRECT_MESSAGE}).exclude(
            card__in=card_ids_with_user_messages).delete()

        # Deleting collabcard state
        ModelUtilities.get_model_filter(collabcardState, {'community': sdk_community_instance.community,
                                                          'card__is_private': True,
                                                          'card__type': card_types.CARD_DIRECT_MESSAGE}).exclude(
            card__in=card_ids_with_user_messages).delete()

        # Deleting conversations
        ModelUtilities.get_model_filter(card_answers, {'community': sdk_community_instance.community,
                                                       'card__is_private': True,
                                                       'card__type': card_types.CARD_DIRECT_MESSAGE}).exclude(
            card__in=card_ids_with_user_messages).delete()

        # Deleting collabcard
        ModelUtilities.get_model_filter(Collabcard, {'community': sdk_community_instance.community,
                                                     'is_private': True,
                                                     'type': card_types.CARD_DIRECT_MESSAGE}).exclude(
            id__in=card_ids_with_user_messages).delete()

        count -= 1


start = time.time()
print("Starting script!")
remove_auto_created_dm_chatrooms_no_messages()
print("Script completed in", time.time() - start)
