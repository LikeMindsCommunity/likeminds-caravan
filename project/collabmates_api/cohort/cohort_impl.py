from django.contrib.auth.models import User
from django.db.models import Count, F
from celery import shared_task

from collabmates_api.cohort.cohort_manager import CohortManager
from external_services.logging.logging_wrapper import LoggingWrapper
from utility.celery_tasks import add_new_participants_to_cohorts_secret_chatroom
from utility.time_utilities import TimeUtilities
from ..chatroom.chatroom_impl import ChatroomImpl
from ..search.sync import ElasticSearchSync
from ..serializers import UserinfoSerializer
from togther.models import ModelUtilities, Members, Community, Cohort, CohortMember, communityRightsSettings, \
    CohortRights, memberRights, userMemberRights, ChatroomCohort, CohortFilter, communityQuestions, communityAnswers
from utility.states import member_states, cohort_types, CohortTypes, cohort_type_list
from ..rest_api import CohortSerializer, CohortMetaSerializer

from ..static_text import create_room_member_right, create_poll_member_right, create_event_member_right, \
    respond_in_rooms_member_right, invite_private_member_right, auto_approve_member_right, create_secret_chatroom_right
from ..user.user_impl import UserImpl, UserHelper
from ..user_moderation_rights import check_all_manager_rights, get_saved_member_rights_list, check_history_exists, \
    check_rights_history_existence, save_member_right, update_member_rights_in_conversation_engage, \
    update_member_rights_in_member_engage
from ..views import get_added_and_removed_rights, get_error_context

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class CohortImpl(CohortManager):
    member_id = None

    def __init__(self, member_id: str = None):
        self.member_id = member_id

    def get_member_id(self) -> str:
        return self.member_id

    def set_member_id(self, member_id: str) -> None:
        self.member_id = member_id

    def create_cohort(self, request_body):

        name = request_body.get('name')
        member_ids = request_body.get('member_ids')
        community_id = request_body.get('community_id')
        type = request_body.get('type', 0)
        type_id = request_body.get('type_id', '')
        filter_list = request_body.get('filter', [])

        if type not in cohort_type_list:
            return {'success': False, 'error_message': "Invalid Cohort Type"}

        if type == cohort_types.SUBSCRIPTION_PLAN and not type_id:
            return {'success': False, 'error_message': "Invalid Type ID"}

        if not name:
            return {'success': False, 'error_message': "Invalid Cohort Name"}

        if not isinstance(member_ids, list):
            return {'success': False, 'error_message': "Invalid Member id List"}

        if not isinstance(filter_list, list):
            return {'success': False, 'error_message': "Invalid Filter List"}

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid User id"}

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return {'success': False, 'error_message': "Invalid Community id"}

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_id,
                                                                  'member_id': user_instance})

        if type in [cohort_types.SUBSCRIPTION_EXPIRED_PLAN, cohort_types.ALL_MEMBER]:

            filter_dict = {
                'type': type,
                'community_id': community_id
            }

            cohort_filter = ModelUtilities.get_model_filter(Cohort, filter_dict)

            if cohort_filter:
                return {'success': False, 'error_message': "This type of cohort already exists in community"}

        if not member_filter:
            return {'success': False, 'error_message': "User is not a member of community"}

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return {'success': False, 'error_message': "User doesn’t have the ability to create cohort"}

        cohort_info = {
            'name': name,
            'community_instance': community_instance,
            'type': type,
        }

        if type == cohort_types.SUBSCRIPTION_PLAN:
            cohort_info['type_id'] = type_id

        cohort_instance = Cohort.create_instance(cohort_info)

        CohortHelper.create_cohort_member_instance(cohort_instance=cohort_instance, member_ids=member_ids)
        CohortHelper.create_cohort_rights_instance(cohort_instance=cohort_instance,
                                                   community_instance=community_instance)

        cohort_instance_object = CohortSerializer(cohort_instance, many=False).data

        if 'rights' in cohort_instance_object:
            admin_rights = check_all_manager_rights(user_instance, community_instance)
            cohort_rights_filter = list(ModelUtilities.get_model_filter(
                CohortRights, {'id__in': cohort_instance_object['rights']}).prefetch_related('member_rights'))
            cohort_rights = CohortHelper.get_all_the_cohort_rights(cohort_rights_filter)
            rights_list = get_saved_member_rights_list(cohort_rights, admin_rights)

            cohort_instance_object['rights'] = rights_list
            cohort_instance_object['cohort_id'] = cohort_instance_object['id']
            del cohort_instance_object['id']

        if filter_list:
            CohortHelper.create_cohort_filters(filter_list, cohort_instance)

        return {'success': True, 'cohort_data': cohort_instance_object}

    def delete_cohort(self, cohort_id):

        cohort_instance = ModelUtilities.get_model_instance_or_none(Cohort, cohort_id)

        if not cohort_instance:
            return {'success': False, 'error_message': "Invalid Cohort id"}

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid User id"}

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': cohort_instance.community_id,
                                                                  'member_id': user_instance})

        if not member_filter:
            return {'success': False, 'error_message': "User is not a member of community"}

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return {'success': False, 'error_message': "User doesn’t have the ability to delete cohort"}

        ModelUtilities.delete_record_in_model(CohortRights, {'cohort': cohort_instance})
        ModelUtilities.delete_record_in_model(CohortMember, {'cohort': cohort_instance})
        ModelUtilities.delete_record_in_model(Cohort, {'id': cohort_id})

        return {'success': True}

    def update_cohort(self, request_body):
        cohort_id = request_body.get('cohort_id')
        name = request_body.get('name')
        member_ids = request_body.get('member_ids')
        rights = request_body.get('rights')
        type = request_body.get('type')
        type_id = request_body.get('type_id')
        filter_list = request_body.get('filter', [])
        community_id = request_body.get('community_id')

        cohort_instance = ModelUtilities.get_model_instance_or_none(Cohort, cohort_id)

        if type not in cohort_type_list:
            return {'success': False, 'error_message': "Invalid Cohort Type"}

        if type == cohort_types.SUBSCRIPTION_PLAN and not type_id:
            return {'success': False, 'error_message': "Invalid Type ID"}

        if not isinstance(member_ids, list):
            return {'success': False, 'error_message': "Invalid Member id List"}

        if not isinstance(filter_list, list):
            return {'success': False, 'error_message': "Invalid Filter List"}

        if not cohort_instance:

            if not type_id and type == cohort_types.SUBSCRIPTION_PLAN:
                return {'success': False, 'error_message': "Invalid type_id"}

            if type == cohort_types.SUBSCRIPTION_EXPIRED_PLAN:
                type_id = None

            if type in [cohort_types.SUBSCRIPTION_EXPIRED_PLAN, cohort_types.ALL_MEMBER] and not community_id:
                return {'success': False, 'error_message:': 'Invalid Community ID'}

            cohort_filter = ModelUtilities.get_model_filter(Cohort, {'type_id': type_id, 'type': type,
                                                                     'community_id': community_id})

            if not cohort_filter:
                return {'success': False, 'error_message': "Invalid cohort_id"}

            cohort_instance = cohort_filter[0]

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid User id"}

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': cohort_instance.community_id,
                                                                  'member_id': user_instance})
        if not member_filter:
            CohortHelper.remove_subscription_based_existing_cohorts(cohort_instance, member_ids)
            self._update_members_for_cohort(cohort_instance, member_ids)
            return {'success': True}

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            CohortHelper.remove_subscription_based_existing_cohorts(cohort_instance, member_ids)
            self._update_members_for_cohort(cohort_instance, member_ids)
            CohortHelper.give_member_rights_when_added_to_cohort(cohort_instance, user_instance)
            return {'success': True}

        update_dict = {'type': type, 'type_id': None}

        if name:
            update_dict['name'] = name

        if type in [cohort_types.SUBSCRIPTION_PLAN, cohort_types.SUBSCRIPTION_EXPIRED_PLAN]:
            update_dict['type_id'] = type_id

        ModelUtilities.model_update(Cohort, {'id': cohort_id}, update_dict)

        if rights:
            existing_rights = set(
                ModelUtilities.get_model_filter(CohortRights, {'cohort': cohort_instance}).values_list(
                    "member_rights__id", flat=True))

            rights_to_add, rights_to_remove = get_added_and_removed_rights(selected_rights=rights,
                                                                           existing_rights=existing_rights)

            user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())
            admin_rights = check_all_manager_rights(user_instance, cohort_instance.community)
            can_add_rights = CohortHelper.check_addition_of_rights(rights_to_add, admin_rights)

            self._remove_rights_from_cohort(rights_to_remove, cohort_instance)

            if not can_add_rights:
                return {'success': False,
                        'error_message': 'CM doesn’t have the ability to update the following set of rights'}

            self._add_rights_to_cohort(rights_to_add, cohort_instance)
            CohortHelper.remove_rights_to_all_cohort_members(cohort_instance, rights_to_remove)

        self._update_members_for_cohort(cohort_instance, member_ids)

        if filter_list:
            CohortHelper.create_cohort_filters(filter_list, cohort_instance)

        return {'success': True}

    def fetch_member_cohorts(self, community_id, member_ids):

        if not isinstance(member_ids, list):
            return get_error_context(success=False, error_message="Invalid member_ids list")

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return get_error_context(success=False, error_message="Invalid community_id")

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return get_error_context(success=False, error_message="Invalid member_id passed in headers")

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                  'member_id': user_instance})

        if not member_filter:
            return get_error_context(success=False, error_message="User is not a member of community")

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm or not member_ids:
            member_cohort_dict = CohortHelper.precompute_cohorts_of_members(community_id=community_id,
                                                                            member_ids=[self.get_member_id()])
        else:
            member_cohort_dict = CohortHelper.precompute_cohorts_of_members(community_id=community_id,
                                                                            member_ids=member_ids)

        return {'success': True, 'member_cohorts': member_cohort_dict}

    def fetch_cohorts_with_community_id(self, community_id):
        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return {'success': False, 'error_message': "Invalid community id"}

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid user id"}

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                  'member_id': user_instance})
        if not member_filter:
            return {'success': False, 'error_message': "User is not a member of community"}

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return {'success': False, 'error_message': "User doesn’t have the ability to fetch cohort"}

        cohort_context_list = []

        cohort_list = ModelUtilities.get_model_filter(Cohort, {'community_id': community_id})

        for cohort in cohort_list:
            cohort_context = {
                'cohort_id': cohort.id,
                'name': cohort.name,
                'type': cohort.type,
                'total_members': ModelUtilities.get_model_filter(CohortMember, {'cohort_id': cohort.id}).count()
            }
            cohort_context_list.append(cohort_context)

        return {'success': True, 'cohorts': cohort_context_list}

    def remove_member_from_cohort(self, request_body):
        user_id = request_body.get('user_id', "")
        cohort_id = request_body.get('cohort_id', "")
        cohort_instance = ModelUtilities.get_model_instance_or_none(Cohort, cohort_id)

        if not cohort_instance:
            return {'success': False, 'error_message': "Invalid cohort id"}

        community_instance = cohort_instance.community

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid user id passed in header"}

        cohort_member_instance = ModelUtilities.get_model_instance_or_none(User, user_id)

        if not cohort_member_instance:
            return {'success': False, 'error_message': "Invalid user id to remove"}

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                  'member_id': user_instance})

        if not member_filter:
            return {'success': False, 'error_message': "User is not a member of community"}

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return {'success': False, 'error_message': "User doesn’t have ability to remove member from cohort"}

        chatroom_cohort_filter = ModelUtilities.get_model_filter(ChatroomCohort,
                                                                 {'cohort_id': cohort_id}).prefetch_related('chatroom')

        for chatroom_cohort_instance in chatroom_cohort_filter:
            chatroom_instance = chatroom_cohort_instance.chatroom
            chatroom_id = chatroom_instance.id

            try:
                chatroom_manager = ChatroomImpl(self.get_member_id(), chatroom_id=chatroom_id)
                chatroom_manager.leave_secret_chatroom(user_id)

            except Exception as e:
                error_logger.error(e.args)

        cohort_member = ModelUtilities.get_model_filter(CohortMember, {'cohort_id': cohort_instance,
                                                                       'user_id': cohort_member_instance})

        if not cohort_member:
            return {'success': False, 'error_message': "User with given user id is not a member of cohort."}

        cohort_member.delete()
        ElasticSearchSync.update_member.delay(member_id=user_id, community_id=community_instance.id)

        return {'success': True}

    def fetch_cohorts_with_community_and_cohort_id(self, cohort_id, community_id):

        cohort_instance = ModelUtilities.get_model_instance_or_none(Cohort, cohort_id)

        if not cohort_instance:
            return {'success': False, 'error_message': "Invalid cohort id"}

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return {'success': False, 'error_message': "Invalid community id"}

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid user id"}

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_instance,
                                                                  'member_id': self.get_member_id()})

        if not member_filter:
            return {'success': False, 'error_message': "User is not a member of community"}

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return {'success': False, 'error_message': "User doesn’t have the ability to fetch cohort"}

        member_ids = list(ModelUtilities.get_model_filter(CohortMember, {'cohort_id': cohort_id})
                          .values_list('user_id', flat=True))

        cohort_member_userinfo_dict = CohortHelper.pre_compute_userinfo_with_user_ids(member_ids)

        members = [UserinfoSerializer(cohort_member_userinfo_dict[member_id]) for member_id in member_ids]

        rights = list(ModelUtilities.get_model_filter(CohortRights, {'cohort_id': cohort_id})
                      .prefetch_related('member_rights'))

        admin_rights = check_all_manager_rights(user_instance, community_instance)
        cohort_rights = CohortHelper.get_all_the_cohort_rights(rights)
        rights_list = get_saved_member_rights_list(cohort_rights, admin_rights)

        cohorts = {'name': cohort_instance.name,
                   'type': cohort_instance.type,
                   'members': members,
                   'member_count': len(members),
                   'rights': rights_list}

        if cohorts.get('type') in [cohort_types.SUBSCRIPTION_PLAN, cohort_types.SUBSCRIPTION_EXPIRED_PLAN]:
            cohorts['type_id'] = cohort_instance.type_id

        return {'success': True, 'cohorts': cohorts}

    def add_user_to_subscription_plans_when_membership_approved(self, community_id):
        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid User ID"}

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return {'success': False, 'error_message': "Invalid Community ID"}

        subscriptions = UserHelper.fetch_user_subscriptions(self.get_member_id(), community_id=community_id)

        if not subscriptions:
            return {'success': False, 'error_message': "User has no subscription for this community"}

        for subscription in subscriptions:
            valid_till = subscription.get('valid_till')
            grace_period = subscription.get('grace_period')
            current_time = TimeUtilities.current_time_in_milliseconds()

            if subscription.get('plan'):

                if current_time < valid_till + grace_period:
                    request_body = {
                        'member_ids': [int(self.get_member_id())],
                        'type': cohort_types.SUBSCRIPTION_PLAN,
                        'type_id': subscription['plan'].get('plan_id')
                    }

                    self.update_cohort(request_body)

        return {'success': True}

    def _remove_rights_from_cohort(self, rights_to_remove, cohort_instance):
        CohortRights.objects.filter(cohort=cohort_instance, member_rights_id__in=rights_to_remove).delete()

    def _add_rights_to_cohort(self, rights_to_add, cohort_instance):

        for right_id in rights_to_add:

            try:
                right = memberRights.objects.get(pk=right_id)
                CohortRights(cohort=cohort_instance, member_rights=right).save()
                CohortHelper.give_rights_to_all_cohort_members(cohort_instance, right)

            except:
                error_logger.error(f"rights already exists for cohort {cohort_instance}")

    def _update_members_for_cohort(self, cohort_instance, member_ids):
        # Doesn't remove any existing member
        existing_cohort_members = set(
            ModelUtilities.get_model_filter(CohortMember, {'cohort_id': cohort_instance.id}).values_list('user_id',
                                                                                                         flat=True))
        members_to_add = list(set(member_ids) - existing_cohort_members)
        CohortHelper.create_cohort_member_instance(cohort_instance=cohort_instance, member_ids=members_to_add)

        if members_to_add:
            add_new_participants_to_cohorts_secret_chatroom.delay(cohort_instance.id, self.get_member_id(), member_ids)

        # In case of cohort meta-data update, updating elasticsearch doc.
        else:
            ElasticSearchSync.update_members.delay(member_ids=list(existing_cohort_members),
                                                   community_id=cohort_instance.community_id)


class CohortHelper:

    @staticmethod
    def create_cohort_member_instance(cohort_instance, member_ids):
        bulk_create_list = []
        user_dict = CohortHelper.pre_compute_users_by_member_id_list(member_ids)

        for member_id in member_ids:

            if user_dict.get(str(member_id)):
                create_cohort_member_info = {
                    'cohort_instance': cohort_instance,
                    'user_instance': user_dict.get(str(member_id))
                }

                cohort_member_instance = CohortMember.create_instance_for_bulk_create(create_cohort_member_info)
                bulk_create_list.append(cohort_member_instance)

        ModelUtilities.bulk_create_instances(CohortMember, bulk_create_list)
        ElasticSearchSync.update_members.delay(member_ids=member_ids, community_id=cohort_instance.community_id)

    @staticmethod
    def create_cohort_rights_instance(cohort_instance, community_instance):
        bulk_create_list = []
        member_rights = communityRightsSettings.objects.select_related('right').filter(
            community=community_instance).order_by("right__state")

        for right in member_rights:
            cohort_right_info = {
                'cohort_instance': cohort_instance,
                'right_instance': right.right
            }
            cohort_right_instance = CohortRights.create_instance_for_bulk_create(cohort_right_info)
            bulk_create_list.append(cohort_right_instance)

        ModelUtilities.bulk_create_instances(CohortRights, bulk_create_list)

    @staticmethod
    def pre_compute_users_by_member_id_list(member_ids):
        user_filter = ModelUtilities.get_model_filter(User, {'id__in': member_ids})
        user_dict = {str(member_id): None for member_id in member_ids}

        for data in user_filter:

            if user_dict.get(data.id) is None:
                user_dict[str(data.id)] = data

        return user_dict

    @staticmethod
    def pre_compute_userinfo_with_user_ids(user_ids):
        user_filter = ModelUtilities.get_model_filter(User, {'id__in': user_ids})
        userinfo_dict = {user_id: None for user_id in user_ids}

        for user in user_filter:
            user_id = user.id

            if userinfo_dict.get(user_id) is None:
                userinfo_dict[user_id] = user.userinfo

        return userinfo_dict

    @staticmethod
    def get_all_the_cohort_rights(cohort_rights):
        rights = {
            "create_room": False,
            "create_poll": False,
            "create_event": False,
            "respond_in_rooms": False,
            "invite_private": False,
            "auto_approve": False,
            "create_secret_chatroom": False
        }

        for right in cohort_rights:
            right = right.member_rights

            if right.state == create_room_member_right['state']:
                rights['create_room'] = True

            elif right.state == create_poll_member_right['state']:
                rights['create_poll'] = True

            elif right.state == create_event_member_right['state']:
                rights['create_event'] = True

            elif right.state == respond_in_rooms_member_right['state']:
                rights['respond_in_rooms'] = True

            elif right.state == invite_private_member_right['state']:
                rights['invite_private'] = True

            elif right.state == auto_approve_member_right['state']:
                rights['auto_approve'] = True

            elif right.state == create_secret_chatroom_right['state']:
                rights['create_secret_chatroom'] = True

        return rights

    @staticmethod
    def check_addition_of_rights(right_ids, admin_rights):
        can_update = True
        rights = ModelUtilities.get_model_filter(memberRights, {'id__in': right_ids})

        for right in rights:
            if right.state == create_room_member_right['state'] and not admin_rights["delete_room"]:
                return False

            elif right.state == create_poll_member_right['state'] and not admin_rights["delete_room"]:
                return False

            elif right.state == create_event_member_right['state'] and not admin_rights["delete_room"]:
                return False

            elif right.state == respond_in_rooms_member_right['state'] and not admin_rights["delete_room"]:
                return False

            elif right.state == invite_private_member_right['state'] and not admin_rights["approve"]:
                return False

            elif right.state == create_secret_chatroom_right['state'] and not admin_rights["delete_room"]:
                return False

        return can_update

    @staticmethod
    def remove_subscription_based_existing_cohorts(cohort_instance, member_ids):
        # Check if type in 1 or 2
        if cohort_instance.type not in [cohort_types.SUBSCRIPTION_PLAN, cohort_types.SUBSCRIPTION_EXPIRED_PLAN]:
            return

        cohort_member_type_filter = ModelUtilities.get_model_filter(CohortMember,
                                                                    {'cohort__type__in': [
                                                                        cohort_types.SUBSCRIPTION_PLAN,
                                                                        cohort_types.SUBSCRIPTION_EXPIRED_PLAN],
                                                                        'user_id__in': member_ids})

        if len(cohort_member_type_filter):
            # Remove existing plans cohort
            cohort_member_type_filter.delete()

    @staticmethod
    def add_all_member_to_cohort(community_id, member_ids, cohort_type=cohort_types.ALL_MEMBER):

        cohort_filter = ModelUtilities.get_model_filter(Cohort,
                                                        {'community_id': community_id,
                                                         'type': cohort_type})

        if not len(cohort_filter):
            return {'error_message': 'No cohort found'}

        cohort_instance = cohort_filter[0]

        # Doesn't remove any existing member
        existing_cohort_members = set(
            ModelUtilities.get_model_filter(CohortMember, {'cohort_id': cohort_instance.id}).values_list('user_id',
                                                                                                         flat=True))

        members_to_add = list(set(member_ids) - existing_cohort_members)
        CohortHelper.create_cohort_member_instance(cohort_instance=cohort_instance, member_ids=members_to_add)

    @staticmethod
    def give_rights_to_all_cohort_members(cohort_instance, right):

        cohort_member_filter = {
            'cohort': cohort_instance
        }

        community_instance = cohort_instance.community

        cohort_members = ModelUtilities.get_model_filter(CohortMember, cohort_member_filter).select_related("user")

        for cohort_member in cohort_members:

            try:
                user = cohort_member.user
                save_member_right(user=user, community=community_instance, right=right)

            except:
                error_logger.error(
                    f"member right already exist for user {cohort_member.user} in community {community_instance.id}")

    @staticmethod
    def remove_rights_to_all_cohort_members(cohort_instance, right_list):

        cohort_member_filter = {
            'cohort': cohort_instance
        }

        community_instance = cohort_instance.community

        cohort_members = ModelUtilities.get_model_filter(CohortMember, cohort_member_filter).select_related("user")

        for cohort_member in cohort_members:

            try:
                user = cohort_member.user

                userMemberRights.objects.filter(user=user, community=community_instance,
                                                right_id__in=right_list).delete()

                update_member_rights_in_member_engage.delay(community_instance.id, user.id)
                update_member_rights_in_conversation_engage.delay(community_instance.id, user.id)

            except:
                error_logger.error(
                    f"member right does not exist for user {cohort_member.user} in community {community_instance.id}")

    @staticmethod
    def give_member_rights_when_added_to_cohort(cohort_instance, user_instance):

        community_instance = cohort_instance.community

        existing_rights = set(ModelUtilities.get_model_filter(CohortRights, {'cohort': cohort_instance})
                              .values_list("member_rights__id", flat=True))

        for right_id in existing_rights:
            right = memberRights.objects.get(id=right_id)

            try:
                save_member_right(user=user_instance, community=community_instance, right=right)

            except:
                error_logger.error(
                    f"member right already exist for user {user_instance.id} in community {community_instance.id}")

    @staticmethod
    def pre_compute_community_answers(member_id, community_id):
        answer_filter = ModelUtilities.get_model_filter(communityAnswers, {'member_id': member_id,
                                                                           'community_id': community_id})

        answer_dict = {}

        for answer in answer_filter:
            community_question_id = answer.question_id

            if answer_dict.get(community_question_id) is None:
                answer_dict[community_question_id] = answer

        return answer_dict

    @staticmethod
    def add_member_to_respective_question_based_cohorts(member_id, community_id):

        answer_dict = CohortHelper.pre_compute_community_answers(member_id=member_id, community_id=community_id)
        community_cohorts = ModelUtilities.get_model_filter(Cohort, {'community_id': community_id})

        for cohort_instance in community_cohorts:
            answer_mismatched = False

            # Fetch all the Cohort Filters related to cohort
            cohort_filter_dict = CohortHelper.get_cohort_filters_dict_using_cohort_id(cohort_instance.id)

            for question_id in cohort_filter_dict:
                # Fetch supported answers for particular question
                supported_answers = cohort_filter_dict.get(question_id)
                answer_instance = answer_dict.get(question_id)

                if isinstance(supported_answers, type(None)):
                    supported_answers = []

                # If given answer doesn't match with cohort filter supported answers
                if (not answer_instance) or (answer_instance.question_answer not in supported_answers):
                    answer_mismatched = True
                    break

            # If no answer mismatched, add user to cohort.
            if not answer_mismatched:

                cohort_info = {
                    'cohort_id': cohort_instance.id,
                    'type': cohort_instance.type,
                    'type_id': cohort_instance.type_id,
                    'community_id': community_id,
                    'member_ids': [int(member_id)]
                }

                cohort_manager = CohortImpl(member_id=member_id)
                update_cohort_response = cohort_manager.update_cohort(cohort_info)

                if update_cohort_response.get('error_message'):
                    error_logger.error(update_cohort_response)

    @staticmethod
    def remove_cohort_membership_when_updating_community_answers(member_id, community_id):

        answer_dict = CohortHelper.pre_compute_community_answers(member_id=member_id, community_id=community_id)
        community_cohorts = ModelUtilities.get_model_filter(Cohort, {'community_id': community_id})

        for cohort_instance in community_cohorts:
            answer_mismatched = False

            # Fetch all the Cohort Filters related to cohort
            cohort_filter_dict = CohortHelper.get_cohort_filters_dict_using_cohort_id(cohort_instance.id)

            for question_id in cohort_filter_dict:
                # Fetch supported answers for particular question
                supported_answers = cohort_filter_dict.get(question_id)
                answer_instance = answer_dict.get(question_id)

                if isinstance(supported_answers, type(None)):
                    supported_answers = []

                # If given answer doesn't match with cohort filter supported answers
                if (not answer_instance) or (answer_instance.question_answer not in supported_answers):
                    answer_mismatched = True
                    break

            # If any answer mismatched, remove user from cohort.
            if answer_mismatched:

                filter_dict = {
                    'cohort_id': cohort_instance.id,
                    'user_id': member_id
                }

                cohort_member_filter = ModelUtilities.get_model_filter(CohortMember, filter_dict)

                if not cohort_member_filter:
                    continue

                # get cohorts related to chatroom
                chatroom_cohort_filter = ModelUtilities.get_model_filter(
                    model=ChatroomCohort,
                    filter_dict={'cohort_id': cohort_instance.id}
                ).prefetch_related('chatroom')

                for chatroom_cohort_instance in chatroom_cohort_filter:
                    chatroom_instance = chatroom_cohort_instance.chatroom
                    chatroom_id = chatroom_instance.id

                    try:
                        chatroom_manager = ChatroomImpl(member_id, chatroom_id=chatroom_id)
                        chatroom_manager.leave_secret_chatroom(member_id=member_id)

                    except Exception as e:
                        error_logger.error(e.args)

                cohort_member_filter.delete()

    @staticmethod
    def precompute_cohorts_of_members(community_id, member_ids):
        community_cohort_filter = ModelUtilities.get_model_filter(Cohort, {'community_id': community_id})
        community_cohort_ids = list(community_cohort_filter.values_list('id', flat=True))
        user_cohort_filter = {
            'cohort_id__in': community_cohort_ids,
            'user_id__in': member_ids
        }
        member_cohort_filter = ModelUtilities.get_model_filter(CohortMember, user_cohort_filter).select_related(
            'cohort')
        member_cohort_dict = {int(user_id): None for user_id in member_ids if str(user_id).isdigit()}

        for data in member_cohort_filter:
            user_id = data.user_id
            cohort_context = CohortMetaSerializer(data.cohort, many=False).data

            if member_cohort_dict.get(user_id) is None:
                member_cohort_dict[user_id] = [cohort_context]

            else:
                member_cohort_dict[user_id].append(cohort_context)

        return member_cohort_dict

    @staticmethod
    def get_cohort_filters_dict_using_cohort_id(cohort_id):
        cohort_filter_dict = dict()
        cohort_instance = ModelUtilities.get_model_instance_or_none(Cohort, cohort_id)

        if not cohort_instance:
            return cohort_filter_dict

        filtered_cohort_filter = ModelUtilities.get_model_filter(CohortFilter, {'cohort_id': cohort_id})

        if not filtered_cohort_filter:
            return cohort_filter_dict

        for cohort_filter in filtered_cohort_filter:
            community_question_id = cohort_filter.question_id

            if cohort_filter_dict.get(community_question_id) is None:
                cohort_filter_dict[community_question_id] = [cohort_filter.value]

            else:
                cohort_filter_dict[community_question_id].append(cohort_filter.value)

        return cohort_filter_dict

    @staticmethod
    def create_cohort_filters(filter_list, cohort_instance):

        cohort_filter_dict = CohortHelper.get_cohort_filters_dict_using_cohort_id(cohort_instance.id)

        for filter_object in filter_list:

            filter_question_id = filter_object.get('question_id')
            filter_value = filter_object.get('value')

            question_instance = ModelUtilities.get_model_instance_or_none(communityQuestions, filter_question_id)

            if not question_instance:
                continue

            existing_question_filter = cohort_filter_dict.get(filter_question_id)

            if isinstance(existing_question_filter, type(None)):
                existing_question_filter = []

            if filter_value not in existing_question_filter:
                cohort_filter_data = {
                    'cohort': cohort_instance,
                    'question': question_instance,
                    'value': filter_value
                }
                CohortFilter.create_instance(cohort_filter_data)
