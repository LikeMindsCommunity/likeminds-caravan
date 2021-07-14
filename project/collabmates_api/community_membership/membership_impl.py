from typing import Union

from django.db.models import Count
from django.contrib.auth.models import User

from collabmates_api.rest_api import CommunitySerializerV1

from togther.models import (Community, Members, card_answers, collabcardState,
                            userEmails, removedMembers, ModelUtilities, communityToast, conversationEngage,
                            SubscriptionExpiredMembers)

from utility.states import member_states, conversation_states, email_states
from utility.states import deleted_members as removed_member_states
from utility.time_utilities import TimeUtilities
from .constants import GET_IN_TOUCH_ROUTE

from .membership_manager import MembershipManager
from ..search.sync import ElasticSearchSync
from ..community.community_impl import CommunityHelper

from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


class MembershipImpl(MembershipManager):
    member_id = None

    def __init__(self, member_id: Union[str, int]):

        self.member_id = member_id

    def get_member_id(self) -> Union[str, int]:
        return self.member_id

    def set_member_id(self, member_id: Union[str, int]) -> None:
        self.member_id = member_id

    def _fetch_serialized_communities_hash(self, serialized_communities):
        return {community['id']: community for community in serialized_communities}

    def _fetch_attended_events_count_of_user(self, community_ids):
        attended_events = collabcardState.objects\
            .filter(
                community_id__in=community_ids,
                user_id=self.get_member_id(),
                attending_status=True,
                is_guest=False)\
            .values('community_id')\
            .annotate(event_count=Count('community_id'))

        return {community['community_id']: community['event_count'] for community in attended_events}

    def _fetch_participated_chatrooms_count_of_user(self, community_ids):
        participated_chatrooms = card_answers.objects\
            .filter(
                community_id__in=community_ids,
                user_id=self.get_member_id(),
                state=conversation_states.ANSWER)\
            .only('community_id')\
            .distinct('card_id')

        card_count_hash = {community_id: 0 for community_id in community_ids}

        for chatroom in participated_chatrooms:
            card_count_hash[chatroom.community_id] += 1

        return card_count_hash

    def _fetch_member_count_for_communities(self, community_ids):

        state_list = [member_states.ADMIN, member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]

        community_members = Members.objects.filter(
            community_id_id__in=community_ids, state__in=state_list)\
            .values('community_id_id')\
            .annotate(members_count=Count('community_id_id'))

        return {members['community_id_id']: members['members_count'] for members in community_members}

    def _fetch_owner_mails_for_communities(self, community_ids):

        community_owners = Members.objects.filter(
            community_id_id__in=community_ids, is_owner=True)\
            .values('member_id_id', 'community_id_id')

        member_id_list = [owner['member_id_id']for owner in community_owners]

        owner_emails = userEmails.objects\
            .filter(user_id__in=member_id_list, email_state=email_states.PRIMARY)\
            .values('user_id', 'email')

        email_hash = {email['user_id']: email['email'] for email in owner_emails}

        return {owner['community_id_id']: email_hash[owner['member_id_id']] for owner in community_owners}

    def _process_benefits(self, community_ids, community_hash, attended_events, participated_rooms, member_count, owner_mails):

        benefit_data = []

        for community_id in community_ids:

            if community_hash.get(community_id):

                benefit_dict = {
                    'events_attended': attended_events.get(community_id, 0),
                    'chatroom_participated': participated_rooms.get(community_id, 0),
                    'community_members': member_count.get(community_id, 0),
                    'get_in_touch_route': GET_IN_TOUCH_ROUTE % owner_mails.get(community_id),
                    'community': community_hash.get(community_id)
                }

                if not owner_mails.get(community_id):
                    del benefit_dict['get_in_touch_route']

                benefit_data.append(benefit_dict)

        return benefit_data

    def fetch_community_benefits(self, community_ids):
        communities = MembershipHelper.fetch_community_instances(community_ids)

        serialized_communities = CommunitySerializerV1(communities, many=True).data

        community_hash = self._fetch_serialized_communities_hash(serialized_communities)

        attended_events = self._fetch_attended_events_count_of_user(community_ids)

        participated_rooms = self._fetch_participated_chatrooms_count_of_user(community_ids)

        member_count = self._fetch_member_count_for_communities(community_ids)

        owner_mails = self._fetch_owner_mails_for_communities(community_ids)

        community_benefits = self._process_benefits(community_ids, community_hash, attended_events, participated_rooms,
                                                    member_count, owner_mails)

        return {
            "success": True,
            "community_benefits": community_benefits
        }

    def remove_community_membership(self, community_id, member_id) -> dict:
        remove_state = removed_member_states.MEMBERSHIP_EXPIRED

        user_instance = User.get_user_or_raise_exception(member_id)
        community_instance = MembershipHelper.fetch_community_instance(community_id)

        is_member_removed = ModelUtilities.get_model_filter(removedMembers,
                                                          {
                                                              "member": user_instance,
                                                              "community": community_instance
                                                          })

        if not is_member_removed:

            member_queryset = ModelUtilities.get_model_filter(Members,
                                                              {
                                                                  "member_id": user_instance,
                                                                  "community_id": community_instance
                                                              })

            if member_queryset:
                member_instance = member_queryset[0]
                SubscriptionExpiredMembers.create_instance_from_member(member_instance)

                member_queryset.delete()

            else:
                return {"success": True}

            instance = removedMembers(community=community_instance, member=user_instance,
                                      removed_state=remove_state, created_at=TimeUtilities.current_time_in_sec())
            instance.save()

            ModelUtilities.delete_record_in_model(conversationEngage,
                                                  {
                                                      "community": community_id,
                                                      "user": member_id
                                                  })

            filter_dict = {'community': community_instance, 'user': user_instance}

            update_dict = {
                'remove': instance,
                'updated_at': TimeUtilities.current_time_in_sec()
            }

            ModelUtilities.model_update(collabcardState, filter_dict, update_dict)

            update_dict = {
                'remove': None,
                'last_updated': TimeUtilities.current_time_in_milliseconds()
            }

            ModelUtilities.model_update(card_answers, filter_dict, update_dict)

            ElasticSearchSync.delete_chatrooms_for_removed_member.delay(community_id, member_id)

        return {"success": True}

    def renew_community_membership(self, community_id) -> dict:

        user_instance = User.get_user_or_raise_exception(self.get_member_id())
        community_instance = MembershipHelper.fetch_community_instance(community_id)

        expired_member_queryset = ModelUtilities.get_model_filter(SubscriptionExpiredMembers,
                                                                  {
                                                                      "member": user_instance,
                                                                      "community": community_instance
                                                                  })

        if expired_member_queryset:
            expired_member_instance = expired_member_queryset[0]
            Members.create_instance_from_expired_member_instace(expired_member_instance)

            expired_member_queryset.delete()

        else:
            return {"success": True}

        ModelUtilities.delete_record_in_model(removedMembers,
                                              {
                                                  "community": community_instance,
                                                  "member": user_instance
                                              })

        filter_dict = {'community': community_instance, 'user': user_instance}

        update_dict = {
            'remove': None,
            'updated_at': TimeUtilities.current_time_in_sec()
        }

        ModelUtilities.model_update(collabcardState, filter_dict, update_dict)

        update_dict = {
            'remove': None,
            'last_updated': TimeUtilities.current_time_in_milliseconds()
        }

        ModelUtilities.model_update(card_answers, filter_dict, update_dict)

        CommunityHelper.update_followed_chatrooms_for_rejoined_member(user_instance, community_instance)

        return {"success": True}


class MembershipHelper:

    @staticmethod
    def fetch_community_instances(community_ids):
        return Community.objects.filter(pk__in=community_ids)

    @staticmethod
    def fetch_community_instance(community_id):
        return Community.get_community_or_raise_exception(community_id)
