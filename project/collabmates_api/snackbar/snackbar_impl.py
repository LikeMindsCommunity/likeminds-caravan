from django.db.models import Q
from collabmates_api.snackbar.snackbar_manager import SnackbarManager
from external_services.logging.logging_wrapper import LoggingWrapper
from togther.models import homeSnackbar, get_user_or_raise_exception, collabcardState, Collabcard, \
    inActiveChatroomsCount
from utility.states import HomeSnackbarType
from utility.time_utilities import TimeUtilities
from .constants import *
from urllib.parse import quote

error_logger = LoggingWrapper.get_instance()


class SnackbarImpl(SnackbarManager):

    def _create_instance_of_home_snackbar(self, user_instance, text, cta, cta_route) -> None:

        instance = homeSnackbar()
        instance.user = user_instance
        instance.text = text
        instance.cta = cta
        instance.cta_route = cta_route
        instance.save()

    @staticmethod
    def _compute_snackbar_dict_for_removed_member(snackbar_dict) -> {}:

        create_dict = {
            'text': REMOVED_MEMBER_SNACKBAR_TEXT % snackbar_dict['community_name'],
            'cta': REMOVED_MEMBER_CTA_TEXT,
        }

        if snackbar_dict['reason']:
            create_dict['cta_route'] = quote(REMOVED_MEMBER_CTA_ROUTE_WITH_REASON % (str(snackbar_dict['tag_id']),
                                                                                     str(snackbar_dict['reason']),
                                                                                     snackbar_dict['community_name']))

        else:
            create_dict['cta_route'] = quote(
                REMOVED_MEMBER_CTA_ROUTE_WITHOUT_REASON % (str(snackbar_dict['tag_id']),
                                                           snackbar_dict['community_name']))

        return create_dict

    def _process_snackbar_dict_for_chatroom_deleted_by_creator(self, snackbar_dict) -> {}:

        chatroom_id = snackbar_dict['chatroom_id']
        card_instance = Collabcard.get_chatroom_or_raise_exception(chatroom_id)
        text = CHATROOM_CREATOR_TEXT % card_instance.header
        cta = CHATROOM_CREATOR_CTA_TEXT
        cta_route = quote(CHATROOM_CREATOR_CTA_ROUTE)
        state_filter = collabcardState.objects.filter(card=chatroom_id, follow_status=True, remove=None)

        for data in state_filter:
            user_instance = data.user
            self._create_instance_of_home_snackbar(user_instance, text, cta, cta_route)

    @staticmethod
    def _compute_cta_route_in_chatroom_manager_delete(tag_id, reason) -> str:

        cta_route = CHATROOM_COMMUNITY_MANAGER_WITHOUT_TAG_REASON_CTA_ROUTE

        if tag_id and not reason:
            cta_route = CHATROOM_COMMUNITY_MANAGER_WITH_TAG_CTA_ROUTE

        elif tag_id and reason:
            cta_route = CHATROOM_COMMUNITY_MANAGER_WITH_TAG_REASON_CTA_ROUTE

        return cta_route

    @staticmethod
    def _compute_inactive_chatrooms_text(member_id) -> str:

        current_time = TimeUtilities.current_time_in_sec()
        inactive_filter = inActiveChatroomsCount.objects.filter(user=member_id)
        inactive_chatrooms_text = ""

        if inactive_filter.exists():
            last_session = inactive_filter[0].updated_at

            inactive_chatrooms = collabcardState.objects.filter(user=member_id, follow_status=True,
                                                                remove=None).filter(~Q(expiry_time=None) & Q(
                expiry_time__lt=current_time) & Q(expiry_time__gt=last_session)).order_by('-expiry_time')

            inactive_chatroom_count = inactive_chatrooms.count()

            if inactive_chatroom_count:
                inactive_chatrooms_text = IN_ACTIVE_CHATROOM_TEXT % (str(inactive_chatroom_count))
                inactive_filter.update(updated_at=current_time)

        else:
            inactive_chatrooms = collabcardState.objects.filter(user=member_id, follow_status=True,
                                                                remove=None).filter(
                ~Q(expiry_time=None) & Q(expiry_time__lt=current_time)).order_by('-expiry_time')

            user_instance = get_user_or_raise_exception(member_id)
            inactive_count = inactive_chatrooms.count()
            inActiveChatroomsCount.create_instance(user_instance, inactive_count)

            if inactive_count:
                inactive_chatrooms_text = IN_ACTIVE_CHATROOM_TEXT % (str(inactive_count))

        return inactive_chatrooms_text

    @staticmethod
    def _fetch_snackbar_query(member_id) -> list:
        return homeSnackbar.objects.filter(user=member_id).order_by('created_at')

    @staticmethod
    def _serialize_snackbar(snackbar_instance) -> {}:

        context = {'text': snackbar_instance.text, 'cta': snackbar_instance.cta,
                   'cta_route': snackbar_instance.cta_route}

        return context

    @staticmethod
    def _delete_snackbar(member_id) -> int:

        delete_count = homeSnackbar.objects.filter(user=member_id).delete()

        return delete_count

    def _process_snackbar_dict_for_chatroom_deleted_by_chatroom_manager(self, snackbar_dict) -> {}:

        chatroom_id = snackbar_dict['chatroom_id']
        card_instance = Collabcard.get_chatroom_or_raise_exception(chatroom_id)

        state_filter = collabcardState.objects.filter(card=chatroom_id, follow_status=True, remove=None)
        text = CHATROOM_COMMUNITY_MANAGER_TEXT % card_instance.header
        cta = CHATROOM_COMMUNITY_MANAGER_CTA_TEXT
        cta_route = quote(self._compute_cta_route_in_chatroom_manager_delete(snackbar_dict['tag_id'], snackbar_dict['reason']))

        text_creator = CHATROOM_COMMUNITY_MANAGER_CREATOR_TEXT % card_instance.header

        for data in state_filter:
            user_instance = data.user

            if user_instance.id == snackbar_dict['chatroom_creator_id']:
                self._create_instance_of_home_snackbar(user_instance, text_creator, cta, cta_route)

            else:
                self._create_instance_of_home_snackbar(user_instance, text, cta, cta_route)

    def _inactive_chatrooms_list(self, member_id) -> list:

        inactive_list = []
        inactive_chatrooms_text = self._compute_inactive_chatrooms_text(member_id)

        if inactive_chatrooms_text:
            inactive_chatroom_context = {
                'cta': IN_ACTIVE_CHATROOM_CTA,
                'cta_route': quote(IN_ACTIVE_CHATROOM_CTA_ROUTE),
                'text': inactive_chatrooms_text
            }
            inactive_list.append(inactive_chatroom_context)

        return inactive_list

    def create_snackbar(self, snackbar_dict) -> None:

        if not SnackbarImplHelper.validate_snackbar_type(snackbar_dict['type']):
            error_logger.error("home snackbar does not support type = %s" % (str(snackbar_dict['type'])))

            return

        if snackbar_dict['type'] == HomeSnackbarType.REMOVED_MEMBER:
            user_instance = get_user_or_raise_exception(snackbar_dict['user_id'])
            create_dict = self._compute_snackbar_dict_for_removed_member(snackbar_dict)
            self._create_instance_of_home_snackbar(user_instance, create_dict['text'],
                                                   create_dict['cta'], create_dict['cta_route'])

        elif snackbar_dict['type'] == HomeSnackbarType.CHATROOM_DELETED_BY_CREATOR:
            self._process_snackbar_dict_for_chatroom_deleted_by_creator(snackbar_dict)

        elif snackbar_dict['type'] == HomeSnackbarType.CHATROOM_DELETED_BY_COMMUNITY_MANAGER:
            self._process_snackbar_dict_for_chatroom_deleted_by_chatroom_manager(snackbar_dict)

        elif snackbar_dict['type'] == HomeSnackbarType.CHATROOM_REJECTED_BY_COMMUNITY_MANAGER:
            user_instance = get_user_or_raise_exception(snackbar_dict['user_id'])
            self._create_instance_of_home_snackbar(user_instance, CHATROOM_REJECTED_BY_MANAGER_TEXT, None, None)

    def fetch_snackbar(self, member_id) -> {}:

        snackbar = []
        snackbar_filter = self._fetch_snackbar_query(member_id)

        for snackbar_instance in snackbar_filter:
            temp = self._serialize_snackbar(snackbar_instance)
            snackbar.append(temp)

        inactive_chatrooms = self._inactive_chatrooms_list(member_id)
        snackbar = snackbar + inactive_chatrooms
        snackbar_context = {
            'snackbars': snackbar
        }
        self._delete_snackbar(member_id)

        return snackbar_context


class SnackbarImplHelper:

    @staticmethod
    def validate_snackbar_type(snackbar_type) -> bool:
        return HomeSnackbarType.has_value(snackbar_type)

