from __future__ import absolute_import, unicode_literals
from celery import shared_task
from external_services.logging.logging_wrapper import LoggingWrapper
from togther.models import (Members, collabcardState, Userinfo, Collabcard,
                            memberRights, adminRights, userAdminRights, userMemberRights,
                            moderationHistory, Report, Report_Tags, communityRightsSettings,
                            Community, removedMembers, userMemberRightsHistory,
                            Member_Engage, conversationEngage)
from utility.states import (member_states, manager_rights, member_rights, moderation_history_types, SyncTypes)
from django.contrib.auth.models import User
from django.db.models import Q
from .static_text import *
import time
import json
from utility.time_utilities import TimeUtilities

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()


def give_all_member_rights(user, community):
    """function to give a member all the rights """
    userMemberRights.objects.filter(user=user, community=community).delete()

    member_rights = memberRights.objects.all().exclude(state__in=[4, 7]).order_by("state")
    fill_member_rights(user, community, member_rights)


def give_default_member_rights(user, community):
    """function to give default member rights to a user """

    if not isinstance(user, User):
        user = User.objects.get(pk=user)

    if not isinstance(community, Community):
        community = Community.objects.get(pk=community)

    userMemberRights.objects.filter(user=user, community=community).delete()

    member_rights_list = memberRights.objects.all().exclude(state=4).order_by("state")

    community_settings = list(communityRightsSettings.objects.filter(community=community).exclude(right__state=4)
                              .values_list("right__state", flat=True))

    rights_added = []
    rights_removed = []
    for right in member_rights_list:

        if right.state == member_rights.MEMBER_RIGHT_CREATE_SECRET_ROOM:
            rights_removed.append(right.id)
            continue

        try:
            if right.state in community_settings:
                rights_added.append(right.state)
                userMemberRights(user=user, community=community, right=right).save()
            else:
                rights_removed.append(right.id)
        except:
            error_logger.error(f"member right already exist for user {user.id} in community {community.id}")

    rights_added = json.dumps(rights_added)

    Member_Engage.objects.filter(member_id=user,
                                 community_id=community).update(rights_list=rights_added,
                                                                updated_at=TimeUtilities.current_time_in_sec())

    conversationEngage.objects.filter(user=user,
                                      community_id=community).update(rights_list=rights_added)



def give_all_manager_rights(user, community):
    """function to give a manager all the rights """
    userAdminRights.objects.filter(user=user, community=community).delete()

    admin_rights = adminRights.objects.all().order_by("state")
    fill_admin_rights(user, community, admin_rights)


def give_default_manager_rights_list(user, community):
    """ function to save default CM rights to a user in a community """
    if not isinstance(user, User):
        user = User.objects.get(pk=user)

    if not isinstance(community, Community):
        community = Community.objects.get(pk=community)

    userMemberRights.objects.filter(user=user, community=community).delete()

    exclude_state_list = [manager_rights.MANAGER_RIGHT_VIEW_CONTACT_INFO, member_rights.MANAGER_RIGHT_ADD_MANAGERS]
    admin_rights_list = adminRights.objects.all().order_by("state").exclude(state=exclude_state_list)
    fill_admin_rights(user, community, admin_rights_list)


def fill_admin_rights(user, community, rights_list):
    """ function to save CM rights of a user in a community """
    for right in rights_list:
        try:
            userAdminRights(user=user, community=community, right=right).save()
        except:
            error_logger.error(f"manager right already exist for user {user.id} in community {community.id}")


def fill_member_rights(user, community, rights_list):
    """ function to save members rights of a user in a community """
    for right in rights_list:
        save_member_right(user=user, community=community, right=right)


def save_member_right(user, community, right):
    """ function to save individual member right """
    try:
        userMemberRights(user=user, community=community, right=right).save()
    except Exception as e:
        error_logger.error(f"member right already exist for user {user.id} in community {community.id}")


def get_saved_member_rights_list(user_rights, admin_rights=None, show_dm_right=False):
    """ function to return the selected and disabled rights of a member or community settings """
    all_member_rights = memberRights.objects.all().exclude(state=4).order_by("state")
    rights_list = []
    for right in all_member_rights:

        if (right.state == member_rights.MANAGER_RIGHT_ENABLE_DIRECT_MESSAGES) and (not show_dm_right):
            continue

        right_dict = {"id": right.id, "title": right.title, "sub_title": right.sub_title, "state": right.state,
                      "is_selected": False, "is_locked": False}

        if right.state == create_room_member_right['state']:
            right_dict["is_selected"] = user_rights["create_room"]
            if admin_rights:
                right_dict["is_locked"] = not admin_rights["delete_room"]

        elif right.state == create_poll_member_right['state']:
            right_dict["is_selected"] = user_rights["create_poll"]
            if admin_rights:
                right_dict["is_locked"] = not admin_rights["delete_room"]

        elif right.state == create_event_member_right['state']:
            right_dict["is_selected"] = user_rights["create_event"]
            if admin_rights:
                right_dict["is_locked"] = not admin_rights["delete_room"]

        elif right.state == respond_in_rooms_member_right['state']:
            right_dict["is_selected"] = user_rights["respond_in_rooms"]
            if admin_rights:
                right_dict["is_locked"] = not admin_rights["delete_room"]

        elif right.state == invite_private_member_right['state']:
            right_dict["is_selected"] = user_rights["invite_private"]
            if admin_rights:
                right_dict["is_locked"] = not admin_rights["approve"]

        elif right.state == auto_approve_member_right['state']:
            right_dict["is_selected"] = user_rights["auto_approve"]
            right_dict["is_locked"] = False

        elif right.state == create_secret_chatroom_right['state']:
            right_dict["is_selected"] = user_rights["create_secret_chatroom"]

            if admin_rights:
                right_dict["is_locked"] = not admin_rights["delete_room"]

        elif right.state == show_direct_messages_right['state']:

            if show_dm_right:
                right_dict["is_selected"] = user_rights["show_dm"]
                right_dict["is_locked"] = False

        if right.sub_title is None:
            del right_dict["sub_title"]

        rights_list.append(right_dict)

    return rights_list


def get_saved_manager_rights_list(admin_rights):
    all_manager_rights = adminRights.objects.all().order_by("state")
    rights_list = []
    for right in all_manager_rights:
        right_dict = {"id": right.id, "title": right.title, "sub_title": right.sub_title,
                      "state": right.state, "is_selected": False}

        if right.state == delete_room_manager_right['state']:
            right_dict["is_selected"] = admin_rights["delete_room"]

        elif right.state == approve_manager_right['state']:
            right_dict["is_selected"] = admin_rights["approve"]

        elif right.state == edit_community_manager_right['state']:
            right_dict["is_selected"] = admin_rights["edit_community"]

        elif right.state == view_contact_manager_right['state']:
            right_dict["is_selected"] = admin_rights["view_contact"]

        elif right.state == add_manager_manager_right['state']:
            right_dict["is_selected"] = admin_rights["add_manager"]

        if right.sub_title is None:
            del right_dict["sub_title"]

        rights_list.append(right_dict)

    return rights_list


def get_default_manager_rights_list():
    all_manager_rights = adminRights.objects.all().order_by("state")
    rights_list = []
    for right in all_manager_rights:
        right_dict = {"id": right.id, "title": right.title, "sub_title": right.sub_title,
                      "state": right.state, "is_selected": False}

        if right.state == delete_room_manager_right['state']:
            right_dict["is_selected"] = True

        elif right.state == approve_manager_right['state']:
            right_dict["is_selected"] = True

        elif right.state == edit_community_manager_right['state']:
            right_dict["is_selected"] = True

        elif right.state == view_contact_manager_right['state']:
            right_dict["is_selected"] = False

        elif right.state == add_manager_manager_right['state']:
            right_dict["is_selected"] = False

        if right.sub_title is None:
            del right_dict["sub_title"]

        rights_list.append(right_dict)

    return rights_list


def check_all_manager_rights(user, community):
    """function to give a manager all the rights """

    admin_rights = userAdminRights.objects.select_related('right').filter(user=user,
                                                                          community=community).order_by("right__state")
    delete_room = False
    approve = False
    edit_community = False
    view_contact = False
    add_manager = False

    rights_list = {"delete_room": delete_room, "approve": approve, "edit_community": edit_community,
                   "view_contact": view_contact, "add_manager": add_manager}

    for right in admin_rights:
        right = right.right

        if right.state == delete_room_manager_right['state']:
            rights_list["delete_room"] = True
        elif right.state == approve_manager_right['state']:
            rights_list["approve"] = True
        elif right.state == edit_community_manager_right['state']:
            rights_list["edit_community"] = True
        elif right.state == view_contact_manager_right['state']:
            rights_list["view_contact"] = True
        elif right.state == add_manager_manager_right['state']:
            rights_list["add_manager"] = True

    return rights_list


def check_all_member_rights(user=None, community=None):
    """function to give a manager all the rights """

    create_room = False
    create_poll = False
    create_event = False
    respond_in_rooms = False
    auto_approve = False
    secret_chatroom = False
    show_direct_messages = False

    if user is None and community is not None:
        member_rights = communityRightsSettings.objects.select_related('right').exclude(right__state=4).filter(
                        community=community).order_by("right__state")

    elif user is not None and community is not None:
        member_rights = userMemberRights.objects.exclude(right__state__in=[4, 7]).select_related(
            'right').filter(user=user,community=community).order_by("right__state")

    else:
        member_rights = []
        respond_in_rooms = True

    for right in member_rights:
        right = right.right

        if right.state == create_room_member_right['state']:
            create_room = True
        elif right.state == create_poll_member_right['state']:
            create_poll = True
        elif right.state == create_event_member_right['state']:
            create_event = True
        elif right.state == respond_in_rooms_member_right['state']:
            respond_in_rooms = True
        elif right.state == auto_approve_member_right['state']:
            auto_approve = True
        elif right.state == create_secret_chatroom_right['state']:
            secret_chatroom = True
        elif right.state == show_direct_messages_right['state']:
            show_direct_messages = True

    rights = {"create_room": create_room, "create_poll": create_poll, "create_event": create_event,
              "respond_in_rooms": respond_in_rooms, "auto_approve": auto_approve,
              "create_secret_chatroom": secret_chatroom, "show_dm": show_direct_messages}

    return rights


def remove_member_create_room_right(user, community, current_user_id):
    create_rights = [member_rights.MEMBER_RIGHT_CREATE_ROOMS, member_rights.MEMBER_RIGHT_CREATE_POLL,
                     member_rights.MEMBER_RIGHT_CREATE_EVENT]
    try:
        userMemberRights.objects.filter(user=user, community=community,
                                        right__state__in=create_rights).delete()

        update_member_rights_history.delay(rights_added=[], rights_removed=create_rights,
                                           current_user_id=current_user_id, community_id=community.id,
                                           user_id=user.id)

    except:
        error_logger.error(f"member right does not exist for user {user.id} in community {community.id}")


def check_admin_delete_right(user, community):
    user_rights = userAdminRights.objects.filter(user=user, community=community,
                                                 right__state=manager_rights.MANAGER_RIGHT_DELETE_ROOMS)

    if user_rights.exists():
        return True
    return False


def check_admin_approve_right(user, community):
    user_rights = userAdminRights.objects.filter(user=user, community=community,
                                                 right__state=manager_rights.MANAGER_RIGHT_APPROVE_REMOVE_MEMBERS)

    if user_rights.exists():
        return True
    return False


def check_admin_view_contact_right(user, community):
    user_rights = userAdminRights.objects.filter(user=user, community=community,
                                                 right__state=manager_rights.MANAGER_RIGHT_VIEW_CONTACT_INFO)

    if user_rights.exists():
        return True
    return False


def check_admin_edit_community_right(user, community):
    user_rights = userAdminRights.objects.filter(user=user, community=community,
                                                 right__state=manager_rights.MANAGER_RIGHT_EDIT_COMMUNITY)

    if user_rights.exists():
        return True
    return False


def get_moderation_history_title(moderation_history):
    if moderation_history.moderation_by:
        user_id = moderation_history.moderation_by.id
        user_name = moderation_history.moderation_by.userinfo.name
    else:
        user_id = 0
        user_name = ''

    community_id = moderation_history.community.id
    title = ""
    if moderation_history.type == moderation_history_types.APPLIED_PUBLIC_LINK:
        title = moderation_history_types.APPLIED_PUBLIC_LINK_TEXT

    elif moderation_history.type == moderation_history_types.APPLIED_PRIVATE_LINK:
        title = moderation_history_types.APPLIED_PRIVATE_LINK_TEXT

    elif moderation_history.type == moderation_history_types.APPROVED_FROM:
        title = moderation_history_types.APPROVED_FROM_TEXT

    elif moderation_history.type == moderation_history_types.MEMBER_PERMISSION_EDITED:
        title = moderation_history_types.MEMBER_PERMISSION_EDITED_TEXT

    elif moderation_history.type == moderation_history_types.MANAGER_PERMISSION_EDITED:
        title = moderation_history_types.MANAGER_PERMISSION_EDITED_TEXT

    elif moderation_history.type == moderation_history_types.MADE_COMMUNITY_MANAGER:
        title = moderation_history_types.MADE_COMMUNITY_MANAGER_TEXT

    elif moderation_history.type == moderation_history_types.REMOVED_AS_COMMUNITY_MANAGER:
        title = moderation_history_types.REMOVED_AS_COMMUNITY_MANAGER_TEXT

    elif moderation_history.type == moderation_history_types.REMOVED_FROM_COMMUNITY:
        title = moderation_history_types.REMOVED_MEMBER_FROM_COMMUNITY_TEXT

    elif moderation_history.type == moderation_history_types.TRANSFERRED_OWNERSHIP:
        title = moderation_history_types.TRANSFERRED_OWNERSHIP_TEXT

    elif moderation_history.type == moderation_history_types.REJOINED_COMMUNITY_PUBLIC_LINK:
        title = moderation_history_types.REJOINED_COMMUNITY_PUBLIC_LINK_TEXT

    elif moderation_history.type == moderation_history_types.REJOINED_COMMUNITY_PRIVATE_LINK:
        title = moderation_history_types.REJOINED_COMMUNITY_PRIVATE_LINK_TEXT

    title = title + f"<<{user_name}|route://member_profile/{user_id}?community_id={community_id}&member_id={user_id}>>"

    if moderation_history.type == moderation_history_types.STARTED_COMMUNITY:
        title = moderation_history_types.STARTED_COMMUNITY_TEXT

    elif moderation_history.type == moderation_history_types.LEFT_COMMUNITY:
        title = moderation_history_types.LEFT_COMMUNITY_TEXT

    elif moderation_history.type == moderation_history_types.APPLIED_PUBLIC_LINK_WEBSITE:
        title = moderation_history_types.APPLIED_PUBLIC_LINK_WEBSITE_TEXT

    history = {"title": title, "moderation_time": moderation_history.moderation_time}

    return history


def check_user_rejoin(user, community):
    """ function to see if user already has moderation history to check rejoining in community"""
    return removedMembers.objects.filter(community=community, member_id=user).exists()
    # return moderationHistory.objects.filter(user=user, community=community).exists()


def save_moderation_history(user, community, moderation_by, type):
    """ function to save moderation history """
    moderationHistory(user=user, community=community, moderation_by=moderation_by, type=type).save()


def check_member_respond_right(user, community):
    user_rights = userMemberRights.objects.filter(user=user, community=community,
                                                  right__state=member_rights.MEMBER_RIGHT_RESPOND_IN_ROOM)

    if user_rights.exists():
        return True
    return False


def check_member_create_room_right(user, community):
    user_rights = userMemberRights.objects.filter(user=user, community=community,
                                                  right__state=member_rights.MEMBER_RIGHT_CREATE_ROOMS)

    if user_rights.exists():
        return True
    return False


def check_member_auto_approve_right(user, community):
    user_rights = userMemberRights.objects.filter(user=user, community=community,
                                                  right__state=member_rights.MEMBER_RIGHT_AUTO_APPROVE)

    if user_rights.exists():
        return True
    return False


def give_member_auto_approve_right(user, community, current_user_instance):
    try:
        approve_right = memberRights.objects.get(state=member_rights.MEMBER_RIGHT_AUTO_APPROVE)
        user_rights = userMemberRights(user=user, community=community,
                                       right=approve_right)
        user_rights.save()

        enable_or_create_member_right_history(user, community, approve_right,
                                              current_user_instance=current_user_instance)
    except:
        error_logger.error(
            f"right {member_rights.MEMBER_RIGHT_CREATE_ROOMS} already exists for user {user.id} in community {community.id}")


def give_member_create_room_right(user, community):
    try:
        user_rights = userMemberRights(user=user, community=community,
                                       right__state=member_rights.MEMBER_RIGHT_CREATE_ROOMS)
        user_rights.save()
    except:
        error_logger.error(
            f"right {member_rights.MEMBER_RIGHT_CREATE_ROOMS} already exists for user {user.id} in community {community.id}")


def give_right_to_all_members(community, right):

    community_id = community.id

    community_members = Members.objects.select_related("member_id").filter(
        community_id=community).filter(Q(state=member_states.MEMBER) |
                                       Q(state=member_states.KNOWN_NOMINATED_PROMOTER) |
                                       Q(state=member_states.PROFILE_UNAVAILABLE))
    for member in community_members:
        try:
            user = member.member_id
            if not check_history_exists(user, community, right, enabled_by_cm=False) or \
                    not check_rights_history_existence(user=user, community=community, right=right):
                save_member_right(user=user, community=community, right=right)

        except:
            error_logger.error(f"member right already exist for user {user.id} in community {community_id}")


def remove_right_for_all_members(community, right):
    community_id = community.id

    community_members = Members.objects.select_related("member_id").filter(
        community_id=community).filter(Q(state=member_states.MEMBER) |
                                       Q(state=member_states.KNOWN_NOMINATED_PROMOTER) |
                                       Q(state=member_states.PROFILE_UNAVAILABLE))
    # has to loop through the members list cause the right should not be deleted for CM's
    for member in community_members:
        try:
            user = member.member_id
            if check_history_exists(user, community, right, enabled_by_cm=False) or \
                    not check_rights_history_existence(user=user, community=community, right=right):
                userMemberRights.objects.filter(user=user, community=community, right=right).delete()

                update_member_rights_in_member_engage.delay(community_id, user.id)
                update_member_rights_in_conversation_engage.delay(community_id, user.id)
        except:
            error_logger.error(f"community settings {community.id} does not have right {right.id} to delete")


def check_history_exists(user, community, right, enabled_by_cm=False):
    rights_history = userMemberRightsHistory.objects.filter(user=user, community=community,
                                                            right=right, enabled_by_CM=enabled_by_cm)
    return rights_history.exists()


def check_rights_history_existence(user, community, right):
    rights_history = userMemberRightsHistory.objects.filter(user=user, community=community, right=right)
    return rights_history.exists()


def get_tool_member_requests(user_id, community_id):
    global tool_member_requests
    member_count = Members.objects.filter(community_id=community_id, state=member_states.PENDING_MEMBER).count()
    tool_member_requests = tool_member_requests.copy()
    tool_member_requests["count"] = member_count

    return tool_member_requests


def get_tool_pending_chat_rooms(user_id, community_id):
    global tool_pending_chat_rooms
    count = Collabcard.objects.filter(community=community_id, is_pending=True, is_deleted=False).count()
    tool_pending_chat_rooms = tool_pending_chat_rooms.copy()
    tool_pending_chat_rooms["count"] = count
    return tool_pending_chat_rooms


def get_tool_review_reports(user_id, community_id, **kwargs):
    global tool_review_reports
    is_owner = kwargs["is_owner"] if "is_owner" in kwargs else False
    parent_cm_list = kwargs["parent_cm_list"] if "parent_cm_list" in kwargs else []
    has_right_0 = kwargs["has_right_0"] if "has_right_0" in kwargs else False
    has_right_1 = kwargs["has_right_1"] if "has_right_1" in kwargs else False
    has_right_2 = kwargs["has_right_2"] if "has_right_2" in kwargs else False

    report_count = get_related_reports_for_user(user_id=user_id, community_id=community_id, has_right_0=has_right_0,
                                                is_owner=is_owner, has_right_1=has_right_1, has_right_2=has_right_2,
                                                parent_cm_list=parent_cm_list, return_reports_count=True)

    tool_review_reports = tool_review_reports.copy()
    tool_review_reports["count"] = report_count
    return tool_review_reports


def get_related_reports_for_user(user_id, community_id, **kwargs):
    if isinstance(user_id, User):
        user_id = user_id.id

    is_owner = kwargs["is_owner"] if "is_owner" in kwargs else False
    parent_cm_list = kwargs["parent_cm_list"] if "parent_cm_list" in kwargs else []
    has_right_0 = kwargs["has_right_0"] if "has_right_0" in kwargs else False
    has_right_1 = kwargs["has_right_1"] if "has_right_1" in kwargs else False
    has_right_2 = kwargs["has_right_2"] if "has_right_2" in kwargs else False
    return_reports_count = kwargs["return_reports_count"] if "return_reports_count" in kwargs else False

    reports = Report.objects.select_related("reported_by", "user_reported", "tag", "action_taken_by",
                                            "action_taken_tag", "community", "collabcard",
                                            "conversation").filter(community=community_id).exclude(type=3).order_by(
        "-id")

    # no once can see those reports which are reported on himself
    reports = reports.exclude(user_reported__id=user_id)
    if not is_owner:

        reports = reports.exclude(user_reported__id__in=parent_cm_list)
        if has_right_0 and not has_right_1 and not has_right_2:
            # if user has only right 0
            reports = reports.exclude(type=0)
        elif has_right_1 and not has_right_0 and not has_right_2:
            # if user has only right 1
            reports = reports.exclude(type__in=[1, 2])

    if return_reports_count:
        reports = reports.exclude(is_closed=True)
        return reports.count()

    return reports


def get_right_dict(right):
    right_dict = {"id": right.id, "state": right.state, "title": right.title}

    if right.sub_title:
        right_dict["sub_title"] = right.sub_title

    return right_dict


def give_all_community_setting_rights(community):
    member_rights = memberRights.objects.all().exclude(state=4).order_by("state")
    save_community_setting_rights(community, member_rights)


def save_community_setting_rights(community, rights_list):
    for right in rights_list:
        try:
            communityRightsSettings(community=community, right=right).save()
        except:
            error_logger.error(f"community settings {community.id} already has right {right.id}")


def remove_all_member_rights(community, user):
    try:
        userMemberRights.objects.filter(user=user, community=community).delete()
        userMemberRightsHistory.objects.filter(user=user, community=community).delete()

    except:
        error_logger.error(f"member rights does not exist to delete for member id {user.id} in {community.id}")


def remove_all_manager_rights(community, user):
    try:
        userAdminRights.objects.filter(user=user, community=community).delete()
    except:
        error_logger.error(
            f"removing all manager rights, manager rights for user {user.id} does not exist in community {community.id} to delete")


@shared_task()
def create_history_for_defaults_rights(rights_added, rights_removed, community_id, user_id):
    community_owner = get_community_owner(community_id)
    update_member_rights_history(rights_added, rights_removed, community_owner.id, community_id, user_id)


@shared_task()
def update_rights_history_for_creation_rights_given(current_user_id, community_id, user_id):
    user = User.objects.get(pk=user_id)
    current_user_instance = User.objects.get(pk=current_user_id)
    community = Community.objects.get(pk=community_id)

    approve_right = memberRights.objects.get(state=member_rights.MEMBER_RIGHT_AUTO_APPROVE)
    enable_or_create_member_right_history(user, community, approve_right,
                                          current_user_instance=current_user_instance)


@shared_task()
def update_rights_history_for_creation_rights_removed(current_user_id, community_id, user_id):
    user = User.objects.get(pk=user_id)
    current_user_instance = User.objects.get(pk=current_user_id)
    community = Community.objects.get(pk=community_id)

    create_rights_list = [member_rights.MEMBER_RIGHT_CREATE_ROOMS, member_rights.MEMBER_RIGHT_CREATE_POLL,
                          member_rights.MEMBER_RIGHT_CREATE_EVENT]

    create_rights = memberRights.objects.filter(state__in=create_rights_list)

    for right in create_rights:
        disable_or_create_member_right_history(user, community,
                                               right_id=right,
                                               current_user_instance=current_user_instance)


@shared_task()
def create_member_rights_history_for_owner(community_id, user_id):
    all_rights = memberRights.objects.all()
    user_instance = User.objects.get(pk=user_id)
    community = Community.objects.get(pk=community_id)

    for right in all_rights:
        enable_or_create_member_right_history(user=user_instance,
                                              community=community,
                                              right_id=right,
                                              current_user_instance=user_instance)


@shared_task()
def update_member_rights_history(rights_added, rights_removed, current_user_id, community_id, user_id):
    current_user_instance = User.objects.get(pk=current_user_id)
    user_instance = User.objects.get(pk=user_id)
    community_instance = Community.objects.get(pk=community_id)

    for right_id in rights_added:
        enable_or_create_member_right_history(user_instance, community_instance, right_id,
                                              current_user_instance=current_user_instance)

    for right_id in rights_removed:
        disable_or_create_member_right_history(user_instance, community_instance, right_id,
                                               current_user_instance=current_user_instance)

    return


def enable_or_create_member_right_history(user, community, right_id, current_user_instance=None):
    rights_history = userMemberRightsHistory.objects.filter(user=user, community=community,
                                                            right=right_id)
    if rights_history.exists():
        rights_history.update(enabled_by_CM=True,
                              updated_CM=current_user_instance, updated_time=time.time())
    else:
        try:
            if isinstance(right_id, memberRights):
                right = right_id
            else:
                right = memberRights.objects.get(pk=right_id)

            create_member_rights_history(right, user, community,
                                         enabled_by_cm=True, updated_cm=current_user_instance)
        except Exception as e:
            error_logger.error(e.args)

    return


def disable_or_create_member_right_history(user, community, right_id, current_user_instance=None):
    rights_history = userMemberRightsHistory.objects.filter(user=user, community=community,
                                                            right=right_id)
    if rights_history.exists():
        rights_history.update(enabled_by_CM=False,
                              updated_CM=current_user_instance, updated_time=time.time())
    else:
        try:
            right = memberRights.objects.get(pk=right_id)
            create_member_rights_history(right, user, community,
                                         enabled_by_cm=False, updated_cm=current_user_instance)
        except Exception as e:
            error_logger.error(e.args)

    return


def create_member_rights_history(right, user, community, enabled_by_cm=False, updated_cm=None):
    userMemberRightsHistory(user=user, community=community, right=right,
                            enabled_by_CM=enabled_by_cm, updated_CM=updated_cm).save()


def restore_member_rights_from_history(user, community):
    userMemberRights.objects.filter(user=user, community=community).delete()

    member_rights = memberRights.objects.all().exclude(state=4)

    rights_list = []
    for right in member_rights:
        # if right enabled by CM or history does not exist for that right to the user in that community
        if check_history_exists(user, community, right, enabled_by_cm=True) or \
                not check_rights_history_existence(user, community, right):
            rights_list.append(right.state)
            save_member_right(user=user, community=community, right=right)

    rights_list = json.dumps(rights_list)

    Member_Engage.objects.filter(member_id=user,
                                 community_id=community).update(rights_list=rights_list,
                                                                updated_at=TimeUtilities.current_time_in_sec())

    conversationEngage.objects.filter(user=user,
                                      community=community).update(rights_list=rights_list)


def get_community_owner(community_obj):
    owner = Members.objects.filter(community_id=community_obj, is_owner=True)

    if owner.exists():
        return owner[0].member_id
    else:
        return get_community_owner_by_time_heirarchy(community_obj)


def get_community_owner_by_time_heirarchy(community_obj):
    members = Members.objects.filter(community_id=community_obj).order_by('id')
    if members.exists():
        return members[0].member_id


def update_manager_rights(rights_added, rights_removed, community_instance, user_instance):
    """ update manager rights from list """
    for right_id in rights_added:
        save_manager_right(right_id, user_instance, community_instance)

    for right_id in rights_removed:
        delete_manager_right(right_id, user_instance, community_instance)


def save_manager_right(right_id, user_instance, community_instance):
    right = adminRights.objects.get(pk=right_id)
    userAdminRights(user=user_instance, community=community_instance, right=right).save()


def delete_manager_right(right_id, user_instance, community_instance):
    right = adminRights.objects.get(pk=right_id)
    userAdminRights.objects.filter(user=user_instance,
                                   community=community_instance, right=right).delete()


def save_added_removed_rights_for_member(community_instance, user_instance, selected_rights):
    # had to get added and removed rights for many other purposes ex: notifications
    existing_rights = set(userMemberRights.objects.filter(community=community_instance,
                                                          user=user_instance).exclude(right__state=4).values_list("right__id", flat=True))
    rights_added, rights_removed = get_added_and_removed_rights(selected_rights=selected_rights,
                                                                existing_rights=existing_rights)
    update_member_rights(rights_added, rights_removed, community_instance, user_instance)

    return rights_added, rights_removed


def update_member_rights(rights_added, rights_removed, community_instance, user_instance):
    """ update member rights from list """
    for right_id in rights_added:
        right = memberRights.objects.get(pk=right_id)
        save_member_right(user=user_instance, community=community_instance, right=right)

    for right_id in rights_removed:
        right = memberRights.objects.get(pk=right_id)
        delete_member_right(user=user_instance, community=community_instance, right=right)


def delete_member_right(user, community, right):
    userMemberRights.objects.filter(user=user,
                                    community=community, right=right).delete()


def get_manager_custom_title(member_instance, custom_title, is_member_already_promoter):
    """ function get community managers custom title """
    custom_title_changed = False
    if not custom_title:
        if not is_member_already_promoter:
            custom_title = "Community Manager"
        else:
            custom_title = member_instance.custom_title

    elif not is_member_already_promoter and custom_title:
        custom_title = custom_title.strip()

        if len(custom_title) <= 0:
            custom_title = None
        elif custom_title == 'Member':
            custom_title = "Community Manager"

    elif is_member_already_promoter and custom_title:
        custom_title = custom_title.strip()
        prev_custom_title = member_instance.custom_title

        if len(custom_title) <= 0:
            custom_title = None
        elif prev_custom_title != custom_title:
            custom_title_changed = True

    return custom_title, custom_title_changed


def get_manager_parents_list(admin_parents, member_parent_list, current_user_id):
    for parent_id in admin_parents:
        if parent_id not in member_parent_list:
            member_parent_list.append(parent_id)
    # adding current user as parent
    if current_user_id not in member_parent_list:
        member_parent_list.append(current_user_id)

    final_parent_list = json.dumps(member_parent_list)
    return final_parent_list


def save_owner_title(custom_title, admin, community_instance, user_instance):
    """ function to update only custom title of owner"""

    if custom_title and len(custom_title.strip()) <= 0:
        custom_title = None

    admin.update(custom_title=custom_title, updated_at=time.time())
    # updating time for all members of community
    Members.objects.filter(community_id=community_instance).update(updated_at=time.time())
    return


def save_added_removed_rights_for_manager(community_instance, user_instance, selected_rights):
    # had to get added and removed rights for many other purposes ex: notifications
    existing_rights = set(userAdminRights.objects.filter(community=community_instance,
                                                         user=user_instance).values_list("right__id", flat=True))
    # getting list of rights added and rights removed when compared to existing rights
    rights_added, removed_rights = get_added_and_removed_rights(selected_rights=selected_rights,
                                                                existing_rights=existing_rights)

    update_manager_rights(rights_added, removed_rights, community_instance, user_instance)

    return rights_added, removed_rights


def get_added_and_removed_rights(selected_rights, existing_rights):
    selected_rights_list = set([right["id"] for right in selected_rights if right["is_selected"]])
    rights_added = selected_rights_list - existing_rights
    removed_rights = existing_rights - selected_rights_list

    return list(rights_added), list(removed_rights)


def save_member_custom_title(custom_title, community_instance, user_instance):
    """ function to update only custom title of owner """
    member_instance = Members.objects.filter(member_id=user_instance, community_id=community_instance)
    custom_title_changed = False

    if custom_title and len(custom_title.strip()) > 0:

        if member_instance.exists():
            prev_custom_title = member_instance[0].custom_title
            custom_title = custom_title.strip()

            if prev_custom_title != custom_title:
                custom_title_changed = True
    else:
        custom_title = None

    member_instance.update(custom_title=custom_title, updated_at=time.time())

    return custom_title_changed


def save_member_rights_in_engage(selected_rights, user_instance, community_instance):
    """ function to save rights list in engage table """
    final_rights = [right["state"] for right in selected_rights if right["is_selected"]]
    rights_list = json.dumps(final_rights)

    Member_Engage.objects.filter(member_id=user_instance,
                                 community_id=community_instance).update(rights_list=rights_list,
                                                                updated_at=TimeUtilities.current_time_in_sec())

    conversationEngage.objects.filter(user=user_instance,
                                      community=community_instance).update(rights_list=rights_list)


@shared_task()
def update_member_rights_in_member_engage(community_id, user_id):
    if isinstance(community_id, Community):
        community = community_id
    else:
        community = Community.objects.get(pk=community_id)

    if isinstance(user_id, User):
        user = user_id
    else:
        user = User.objects.get(pk=user_id)

    rights_list = list(userMemberRights.objects.filter(user=user, community=community).exclude(right__state=4)
                       .values_list("right__state", flat=True))

    rights_list = json.dumps(rights_list)

    Member_Engage.objects.filter(member_id=user,
                                 community_id=community).update(rights_list=rights_list,
                                                                updated_at=TimeUtilities.current_time_in_sec())


@shared_task()
def update_member_rights_in_conversation_engage(community_id, user_id):

    if isinstance(community_id, Community):
        community = community_id
    else:
        community = Community.objects.get(pk=community_id)

    if isinstance(user_id, User):
        user = user_id
    else:
        user = User.objects.get(pk=user_id)

    rights_list = list(userMemberRights.objects.filter(user=user, community=community).exclude(right__state=4)
                       .values_list("right__state", flat=True))

    rights_list = json.dumps(rights_list)
    conversationEngage.objects.filter(user=user,
                                      community_id=community).update(rights_list=rights_list)


@shared_task
def update_member_rights_list_for_community_members(community_id):

    community = Community.objects.get(pk=community_id)
    community_members = Members.objects.select_related("member_id").filter(
        community_id=community).filter(Q(state=member_states.MEMBER) |
                                       Q(state=member_states.PROFILE_UNAVAILABLE)).select_related('member_id')

    for member in community_members:
        user = member.member_id

        update_member_rights_in_member_engage(community, user)
        update_member_rights_in_conversation_engage(community, user)
