from django.contrib.auth.models import User
from django.db.models import Count, F

from collabmates_api.cohort.cohort_manager import CohortManager
from external_services.logging.logging_wrapper import LoggingWrapper
from ..serializers import UserinfoSerializer
from togther.models import ModelUtilities, Members, Community, Cohort, CohortMember, communityRightsSettings, \
    CohortRights, memberRights
from utility.states import member_states

from ..static_text import create_room_member_right, create_poll_member_right, create_event_member_right, \
    respond_in_rooms_member_right, invite_private_member_right, auto_approve_member_right, create_secret_chatroom_right
from ..user_moderation_rights import check_all_manager_rights, get_saved_member_rights_list
from ..views import get_added_and_removed_rights

error_logger = LoggingWrapper.get_instance()


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

        if not member_ids or not isinstance(member_ids, list):
            return {'success': False, 'error_message': "Invalid Member id List"}

        user_instance = ModelUtilities.get_model_instance_or_none(User, self.get_member_id())

        if not user_instance:
            return {'success': False, 'error_message': "Invalid User id"}

        community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)

        if not community_instance:
            return {'success': False, 'error_message': "Invalid Community id"}

        member_filter = ModelUtilities.get_model_filter(Members, {'community_id': community_id,
                                                                  'member_id': user_instance})

        if not member_filter:
            return {'success': False, 'error_message': "User is not a member of community"}

        member_instance = member_filter[0]
        is_cm = member_instance.state == member_states.ADMIN

        if not is_cm:
            return {'success': False, 'error_message': "User doesn’t have the ability to create cohort"}

        cohort_info = {
            'name': name,
            'community_instance': community_instance
        }
        cohort_instance = Cohort.create_instance(cohort_info)

        CohortHelper.create_cohort_member_instance(cohort_instance=cohort_instance, member_ids=member_ids)
        CohortHelper.create_cohort_rights_instance(cohort_instance=cohort_instance,
                                                   community_instance=community_instance)

        return {'success': True}

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

        cohort_instance = ModelUtilities.get_model_instance_or_none(Cohort, cohort_id)

        if not isinstance(member_ids, list):
            return {'success': False, 'error_message': "Invalid Member id List"}

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
            return {'success': False, 'error_message': "User doesn’t have the ability to update cohort"}

        update_dict = {
            'name': name,
        }
        ModelUtilities.model_update(Cohort, {'id': cohort_id}, update_dict)

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
        self._update_members_for_cohort(cohort_instance, member_ids)

        return {'success': True}

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

        cohort_list = list(ModelUtilities.get_model_filter(CohortMember, {'cohort__community_id': community_id})
                           .values('cohort').annotate(total_members=Count('cohort'), name=F('cohort__name')).order_by()
                           .values('name', 'total_members'))

        return {'success': True, 'cohorts': cohort_list}

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

        cohort_member = ModelUtilities.get_model_filter(CohortMember, {'cohort_id': cohort_instance,
                                                                       'user_id': cohort_member_instance})

        if not cohort_member:
            return {'success': False, 'error_message': "User with given user id is not a member of cohort."}

        cohort_member.delete()

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
                   'members': members,
                   'member_count': len(members),
                   'rights': rights_list}

        return {'success': True, 'cohorts': cohorts}

    def _remove_rights_from_cohort(self, rights_to_remove, cohort_instance):

        for right_id in rights_to_remove:

            try:
                right = memberRights.objects.get(pk=right_id)
                CohortRights.objects.filter(cohort=cohort_instance, member_rights=right).delete()
            except:
                error_logger.error(f"rights doesn't exist for cohort {cohort_instance}")

    def _add_rights_to_cohort(self, rights_to_add, cohort_instance):

        for right_id in rights_to_add:

            try:
                right = memberRights.objects.get(pk=right_id)
                CohortRights(cohort=cohort_instance, member_rights=right).save()
            except:
                error_logger.error(f"rights already exists for cohort {cohort_instance}")

    def _update_members_for_cohort(self, cohort_instance, member_ids):
        # Doesn't remove any existing member
        existing_cohort_members = set(
            ModelUtilities.get_model_filter(CohortMember, {'user_id__in': member_ids}).values_list('user_id',
                                                                                                   flat=True))
        members_to_add = list(set(member_ids) - existing_cohort_members)
        CohortHelper.create_cohort_member_instance(cohort_instance=cohort_instance, member_ids=members_to_add)


class CohortHelper:

    @staticmethod
    def create_cohort_member_instance(cohort_instance, member_ids):
        bulk_create_list = []
        user_dict = CohortHelper.pre_compute_users_by_member_id_list(member_ids)

        for member_id in member_ids:

            if user_dict.get(member_id):
                create_cohort_member_info = {
                    'cohort_instance': cohort_instance,
                    'user_instance': user_dict.get(member_id)
                }

                cohort_member_instance = CohortMember.create_instance_for_bulk_create(create_cohort_member_info)
                bulk_create_list.append(cohort_member_instance)

        ModelUtilities.bulk_create_instances(CohortMember, bulk_create_list)

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
        user_dict = {member_id: None for member_id in member_ids}

        for data in user_filter:

            if user_dict.get(data.id) is None:
                user_dict[data.id] = data

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
                rights['secret_chatroom'] = True

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
