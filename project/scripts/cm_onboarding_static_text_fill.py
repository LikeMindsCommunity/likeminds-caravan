from togther.models import GetStarted, ModelUtilities, CommunitySettings, Community, CommunityGetStarted, Members, \
    Collabcard, communityFieldTypes, communityFieldSubTypes, communityField, communityQuestions
from utility.states import get_started_types, card_types, question_states, member_states
from collabmates_api.community.constants import COMMUNITY_SETTING_TYPE_TITLE_MAPPING, \
    COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING
from collabmates_api.views import post_general_collabcard_for_community
from django.db.models import Q
import time
from utility.time_utilities import TimeUtilities
from collabmates_api.static_text import GENERAL_CHAT_TITLE_TEXT, GENERAL_CHAT_HEADER

COMMUNITY_HOOD_COMMUNITY_ID = 49751

get_started_types_object_list = [
    {
        "type": get_started_types.CREATE_COMMUNITY_TYPE,
        "title": "Create community",
        "tool_tip_text": ""
    },
    {
        "type": get_started_types.INVITE_MEMBERS_TYPE,
        "title": "Invite members",
        "tool_tip_text": "Share paid or free links to invite members to join the community."
    },
    {
        "type": get_started_types.CREATE_EVENT_TYPE,
        "title": "Create event",
        "tool_tip_text": "Create an event and invite new members by building top of the funnel."
    },
    {
        "type": get_started_types.CUSTOMISE_JOIN_FORM,
        "title": "Customise join form",
        "tool_tip_text": "Questions your members would be answering before joining the community."
    },
    {
        "type": get_started_types.JOIN_COMMUNITY_HOOD,
        "title": "Join CommunityHood",
        "tool_tip_text": "Join our community of Community Managers to get latest updates about LikeMinds."
    }
]

community_field_type_object = {
    'type': 'default',
    'sub_type_header': 'default',
    'sub_type_placeholder': 'default',
    'rank': 999,
    'created_at': TimeUtilities.current_time_in_sec()
}

community_field_sub_type_object = {
    'type': 'default',
    'sub_type': 'default',
    'rank': 999,
    'created_at': TimeUtilities.current_time_in_sec()
}

basic_directory_questions = [
    {
        "question_title": "Name",
        "value": None,
        "optional": True,
        "state": question_states.PARAGRAPH,
        "help_text": "Your Name",
        "field": True,
        "is_compulsory": True
    },
    {
        "question_title": "Phone Number",
        "value": "[{\"answer_privacy\": \"Private\"}]",
        "optional": True,
        "state": question_states.MOBILE_NO,
        "help_text": "Your mobile number",
        "field": True,
        "is_compulsory": True
    },
    {
        "question_title": "Email",
        "value": "[{\"answer_privacy\": \"Private\"}]",
        "optional": True,
        "state": question_states.EMAIL_ID,
        "help_text": "Your email address",
        "field": True,
        "is_compulsory": False
    }
]


def fill_get_started_data():

    get_started_instances_list = []

    for get_started_types_object in get_started_types_object_list:
        get_started_instance = ModelUtilities.get_model_filter(GetStarted,
                                                               {"type": get_started_types_object.get("type")})

        if not get_started_instance:
            get_started_instances_list.append(GetStarted.create_instance(get_started_types_object))

    if len(get_started_instances_list):
        ModelUtilities.bulk_create_instances(GetStarted, get_started_instances_list)


def check_new_questions_added(community_instance):

    community_questions_filter = ModelUtilities.get_model_filter(communityQuestions,
                                                                 {'community': community_instance})

    if len(community_questions_filter) == 4:

        community_questions_filter = community_questions_filter.filter(Q(question_state=question_states.INTRODUCTION) &
                                                                       Q(question_state=question_states.PARAGRAPH,
                                                                         question_title='NAME') &
                                                                       Q(question_state=question_states.EMAIL_ID,
                                                                         question_title='Email') &
                                                                       Q(question_state=question_states.MOBILE_NO,
                                                                         question_title='Phone Number')
                                                                       )

        if len(community_questions_filter):
            return False

    return True


def check_join_community_hood(community_instance):

    cms_list = list(ModelUtilities.get_model_filter(
        Members, {'community_id': community_instance, 'state': member_states.ADMIN}).values_list('member_id_id',
                                                                                                 flat=True))

    if len(cms_list):
        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': COMMUNITY_HOOD_COMMUNITY_ID,
                                                                  'member_id_id__in': cms_list})

        if len(member_filter):
            return True

    return False


def fill_community_get_started_for_previous_communities():

    all_communities_filter = ModelUtilities.get_model_filter(Community, {})

    create_community_get_started = ModelUtilities.get_model_filter(GetStarted,
                                                                   {'type': get_started_types.CREATE_COMMUNITY_TYPE})

    invite_members_get_started = ModelUtilities.get_model_filter(GetStarted,
                                                                 {'type': get_started_types.INVITE_MEMBERS_TYPE})

    create_event_get_started = ModelUtilities.get_model_filter(GetStarted,
                                                               {'type': get_started_types.CREATE_EVENT_TYPE})

    customise_form_get_started = ModelUtilities.get_model_filter(GetStarted,
                                                                 {'type': get_started_types.CUSTOMISE_JOIN_FORM})

    join_hood_get_started = ModelUtilities.get_model_filter(GetStarted,
                                                            {'type': get_started_types.JOIN_COMMUNITY_HOOD})

    community_get_started_instance_list = list()

    for community_instance in all_communities_filter:
        should_invite_members = False
        should_create_event = False

        community_get_started_filter = ModelUtilities.get_model_filter(CommunityGetStarted,
                                                                       {'community': community_instance})

        if community_get_started_filter:
            continue

        community_get_started_instance_list.append(CommunityGetStarted.create_instance({
            'get_started': create_community_get_started[0],
            'community': community_instance,
            'completed': True
        }))

        # Check if members are there
        members_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                   'is_owner': False})

        if len(members_filter):
            should_invite_members = True

        community_get_started_instance_list.append(CommunityGetStarted.create_instance({
            'get_started': invite_members_get_started[0],
            'community': community_instance,
            'completed': should_invite_members
        }))

        # Check event filter
        event_filter = ModelUtilities.get_model_filter(Collabcard,
                                                       {'community': community_instance,
                                                        'type__in': [card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]})

        if len(event_filter):
            should_create_event = True

        community_get_started_instance_list.append(CommunityGetStarted.create_instance({
            'get_started': create_event_get_started[0],
            'community': community_instance,
            'completed': should_create_event
        }))

        community_get_started_instance_list.append(CommunityGetStarted.create_instance({
            'get_started': customise_form_get_started[0],
            'community': community_instance,
            'completed': check_new_questions_added(community_instance)
        }))

        community_get_started_instance_list.append(CommunityGetStarted.create_instance({
            'get_started': join_hood_get_started[0],
            'community': community_instance,
            'completed': check_join_community_hood(community_instance)
        }))

    if len(community_get_started_instance_list):
        ModelUtilities.bulk_create_instances(CommunityGetStarted, community_get_started_instance_list)


def fill_members_auto_join_community_setting():

    community_filter = ModelUtilities.get_model_filter(Community, {})
    count = len(community_filter)
    community_settings_list = []

    for community_instance in community_filter:

        print('Community Count -->', count)
        count -= 1

        community_setting_filter = ModelUtilities.get_model_filter(CommunitySettings,
                                                                   {'community': community_instance,
                                                                    'setting_type': 'members_auto_join'})

        if community_setting_filter:
            continue

        community_settings_data = {
            'community_instance': community_instance,
            'setting_type': 'members_auto_join',
            'setting_title': COMMUNITY_SETTING_TYPE_TITLE_MAPPING['members_auto_join'],
            'setting_sub_title': COMMUNITY_SETTING_TYPE_SUB_TITLE_MAPPING.get('members_auto_join'),
            'enabled': community_instance.auto_approval
        }
        community_settings_instance = CommunitySettings.create_instance(community_settings_data)
        community_settings_list.append(community_settings_instance)

    ModelUtilities.bulk_create_instances(CommunitySettings, community_settings_list)


def create_community_default_types_and_subtypes():
    # Create communityFieldType Object
    community_field_type_filter = ModelUtilities.get_model_filter(communityFieldTypes,
                                                                  {'type': community_field_type_object.get('type'),
                                                                   'rank': community_field_type_object.get('rank')})

    community_field_type_instance = None

    if not len(community_field_type_filter):
        community_field_type_instance = communityFieldTypes.objects.create(**community_field_type_object)

    if not community_field_type_instance:
        community_field_type_instance = community_field_type_filter[0]

    # Create communityFieldSubType Object
    community_field_sub_type_filter = ModelUtilities.get_model_filter(communityFieldSubTypes,
                                                                      {'type': community_field_type_instance})

    if not len(community_field_sub_type_filter):
        community_field_sub_type_object['type'] = community_field_type_instance
        community_field_sub_type_instance = communityFieldSubTypes.objects.create(**community_field_sub_type_object)


def add_community_field_questions_to_default():
    community_field_type_filter = ModelUtilities.get_model_filter(communityFieldTypes,
                                                                  {'type': community_field_type_object.get('type'),
                                                                   'rank': community_field_type_object.get('rank')})

    if not len(community_field_type_filter):
        return

    community_field_type_instance = community_field_type_filter[0]

    community_field_sub_type_filter = ModelUtilities.get_model_filter(communityFieldSubTypes,
                                                                      {'type': community_field_type_instance})

    if not len(community_field_sub_type_filter):
        return

    community_field_sub_type_instance = community_field_sub_type_filter[0]

    for question_data in basic_directory_questions:
        question_filter = ModelUtilities.get_model_filter(communityField,
                                                          {'type': community_field_type_instance,
                                                           'sub_type': community_field_sub_type_instance,
                                                           'question_title': question_data.get('question_title'),
                                                           'state': question_data.get('state')})

        if not len(question_filter):
            question_data['type'] = community_field_type_instance
            question_data['sub_type'] = community_field_sub_type_instance
            question_instance = communityField.objects.create(**question_data)


def add_general_chatroom_in_previous_communitites():

    all_communities_filter = ModelUtilities.get_model_filter(Community, {})

    communities_count = len(all_communities_filter)

    for community_instance in all_communities_filter:

        print("Communities left", communities_count)
        communities_count -= 1

        filter_dict = {
            'community': community_instance,
            'title': GENERAL_CHAT_TITLE_TEXT,
            'type': card_types.CARD_NORMAL,
            'header': GENERAL_CHAT_HEADER,
        }

        if ModelUtilities.is_model_filter_exists(Collabcard, filter_dict):
            continue

        community_owner_filter = ModelUtilities.get_model_filter(Members,
                                                                 {'community_id': community_instance,
                                                                  'is_owner': True})

        if not len(community_owner_filter):
            continue

        community_owner_instance = community_owner_filter[0]
        post_general_collabcard_for_community(community_instance, community_owner_instance.member_id_id)


print("Started")
started_at = time.time()
fill_get_started_data()
fill_community_get_started_for_previous_communities()
fill_members_auto_join_community_setting()
create_community_default_types_and_subtypes()
add_community_field_questions_to_default()
add_general_chatroom_in_previous_communitites()
print(time.time() - started_at)
