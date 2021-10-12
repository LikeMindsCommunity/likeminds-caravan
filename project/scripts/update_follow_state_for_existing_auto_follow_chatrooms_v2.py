import json
import time
from collabmates_api.search.sync import ElasticSearchSync
from collabmates_api.views import get_expiry_time_of_chatroom, create_chatroom_engagement
from external_services.logging.logging_wrapper import LoggingWrapper
from togther.models import ModelUtilities, Collabcard, Members, collabcardState
from utility.states import member_states, SyncNotificationTypes
from utility.time_utilities import TimeUtilities
from collabmates_api.notification import send_sync_notification

HOURS_24 = 86400

info_logger = LoggingWrapper.get_instance()


def update_follow_state_for_existing_auto_follow_chatrooms_v2():
    chatroom_ids = [
        23660, 23663, 23488, 22846, 23675, 23676, 23647, 23914, 23346, 23717, 23726, 23771, 23811, 23816, 23818,
        23814, 23473, 23837, 23859, 23864, 20542, 14779, 21768, 21935, 22374, 22526, 22795, 22957, 23078, 22985,
        23050, 23140, 23146, 23159, 23061, 23090, 23202, 15512, 23122, 22829, 23240, 23252, 21261, 23288, 21673,
        23043, 22987, 23188, 23335, 23334, 23317, 23321, 23322, 23323, 23325, 23347, 23353, 23292, 23351, 23363,
        23365, 23374, 23434, 23475, 23466, 23457, 23455, 23504, 23567, 14535, 23465, 23580, 23119, 23560, 23508,
        22563, 23590, 23622, 23587, 23623, 23643, 23651, 23656, 12291, 18776, 14678, 15135, 15245, 15500, 15797,
        16290, 16437, 16918, 16913, 17643, 17798, 15929, 17700, 19544, 19813, 19915, 19913, 20032, 20123, 20426,
        20465, 20504, 20562, 20560, 20047, 20661, 20655, 20662, 20671, 20766, 20897, 20976, 21126, 21157, 17944,
        21152, 19927, 21341, 21294, 16067, 21475, 21229, 21161, 21553, 21309, 21195, 19378, 16481, 21384, 21386,
        18053, 16329, 17295, 21394, 17570, 21401, 15105, 15890, 21451, 16641, 21312, 21558, 21118, 8382, 21452,
        21648, 21642, 21851, 21836, 21740, 21678, 16223, 21699, 21713, 21701, 21753, 21762, 21732, 15842, 15846,
        21757, 21916, 21874, 14689, 21939, 21944, 21938, 21943, 21952, 21738, 22053, 22051, 16908, 22147, 22175,
        22208, 22213, 18775, 22593, 16331, 22333, 22327, 22377, 22393, 22651, 22469, 22488, 22468, 22685, 22532,
        22739, 22849, 23039, 22805, 22845, 22869, 22905, 22928, 22649, 22955, 22853, 22998, 7648, 23019, 23141,
        21602, 23973, 22746, 24029, 24041, 24071, 24074, 24064, 24115, 24123, 9692, 24192, 24203, 24211, 24230,
        6244, 24298, 24295, 24314, 15341, 15272, 24482, 23066, 24438, 23531, 23145, 22804, 22714, 23491, 24484,
        22813, 31937, 5710, 31934, 66769, 66746, 66978, 23530, 24443, 20541, 24281, 24437, 24419, 7899, 8490, 14531,
        14562, 14566, 15933, 19084, 22240, 22502]

    filter_dict = {'follow_status': False,
                   'card_id__in': chatroom_ids}

    collabcard_state_filter = ModelUtilities.get_model_filter(collabcardState, filter_dict)

    for state in collabcard_state_filter:
        print("Chatroom ID: {} | User ID: {}".format(state.card_id, state.user_id))
        info_logger.info("Chatroom ID: {} | User ID: {}".format(state.card_id, state.user_id))

        try:
            chatroom_follow(state)

        except Exception as e:
            print(str(e))


def chatroom_follow(card_state_instance):
    follow_status = card_state_instance.follow_status

    if follow_status:
        print("Already Followed")
        return

    status = True
    card_instance = card_state_instance.card
    user_instance = card_state_instance.user
    community_instance = card_instance.community

    member_state = Members.get_community_member_state(community_instance.id, user_instance.id)

    from collabmates_api.conversation.conversation_impl import ConversationHelper

    expiry_time = get_expiry_time_of_chatroom(card_state_instance)

    card_state_filter = ModelUtilities.get_model_filter(collabcardState, {'id': card_state_instance.id})

    card_state_filter.update(follow_status=status, updated_at=TimeUtilities.current_time_in_sec(),
                             expiry_time=expiry_time,
                             external_seen=True, external_follow=status)

    create_chatroom_engagement(card_instance=card_instance, user_instance=user_instance,
                               member_state=member_state)

    ConversationHelper.update_homescreen_meta_on_chatroom_follow(community_instance,
                                                                 card_instance,
                                                                 card_state_instance,
                                                                 user_instance)

    send_sync_notification.delay({'chatroom_id': card_instance.id,
                                  'member_id': user_instance.id,
                                  'sync_notification_type': SyncNotificationTypes.SINGLE_MEMBER.value})

    ElasticSearchSync.update_chatroom_for_user.delay(card_instance.id, user_instance.id)

    if card_instance.is_secret and member_state == member_states.ADMIN and status:
        participants_list = json.loads(card_instance.secret_chatroom_participants)

        if user_instance.id not in participants_list:
            participants_list.append(user_instance.id)
            ModelUtilities.model_update(Collabcard, {'id': card_instance.id},
                                        {'secret_chatroom_participants': json.dumps(participants_list)})


start_time = time.time()
update_follow_state_for_existing_auto_follow_chatrooms_v2()
end_time = time.time()
time_taken = end_time - start_time

print(time_taken)
