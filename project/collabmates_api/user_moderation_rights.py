from togther.models import (Members, collabcardState, Userinfo, Collabcard,
                            memberRights, adminRights, userAdminRights, userMemberRights,
                            moderationHistory)
from utility.states import (member_states, manager_rights, member_rights, moderation_history_types)

from django.db.models import Q
from .static_text import *



def give_all_member_rights(user, community):
    """function to give a member all the rights """
    userMemberRights.objects.filter(user=user, community=community).delete()

    member_rights = memberRights.objects.all().order_by("state")
    fill_member_rights(user, community, member_rights)


def give_all_manager_rights(user, community):
    """function to give a manager all the rights """
    userAdminRights.objects.filter(user=user, community=community).delete()

    admin_rights = adminRights.objects.all().order_by("state")
    fill_admin_rights(user, community, admin_rights)


def fill_admin_rights(user, community, rights_list):
    for right in rights_list:
        userAdminRights(user=user, community=community, right=right).save()


def fill_member_rights(user, community, rights_list):
    for right in rights_list:
        userMemberRights(user=user, community=community, right=right).save()


def get_saved_member_rights_list(user_rights, admin_rights=None):

    all_member_rights = memberRights.objects.all().order_by("state")
    rights_list = []
    for right in all_member_rights:
        right_dict = {"id": right.id, "title": right.title, "sub_title": right.sub_title,
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

        rights_list.append(right_dict)

    return rights_list


def get_saved_manager_rights_list(admin_rights):

    all_manager_rights = adminRights.objects.all().order_by("state")
    rights_list = []
    for right in all_manager_rights:
        right_dict = {"id": right.id, "title": right.title, "sub_title": right.sub_title,
                      "is_selected": False}

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


def check_all_member_rights(user, community):
    """function to give a manager all the rights """

    admin_rights = userMemberRights.objects.select_related('right').filter(user=user,
                                                                           community=community).order_by("right__state")
    create_room = False
    create_poll = False
    create_event = False
    respond_in_rooms = False
    invite_private = False

    for right in admin_rights:
        if right.state == create_room_member_right['state']:
            create_room = True
        elif right.state == create_poll_member_right['state']:
            create_poll = True
        elif right.state == create_event_member_right['state']:
            create_event = True
        elif right.state == respond_in_rooms_member_right['state']:
            respond_in_rooms = True
        elif right.state == invite_private_member_right['state']:
            invite_private = True

    rights = {"create_room": create_room, "create_poll": create_poll, "create_event": create_event,
              "respond_in_rooms": respond_in_rooms, "invite_private": invite_private}

    return rights


def remove_creation_rights_for_user(user, community):
    user_rights = userMemberRights.objects.filter(user=user, community=community).filter(
                                                  Q(right__state=member_rights.MEMBER_RIGHT_CREATE_ROOMS) |
                                                  Q(right__state=member_rights.MEMBER_RIGHT_CREATE_POLL) |
                                                  Q(right__state=member_rights.MEMBER_RIGHT_CREATE_EVENT))
    user_rights.delete()


def check_admin_delete_right(user, community):

    user_rights = userAdminRights.objects.filter(user=user, community=community,
                                                 state=manager_rights.MANAGER_RIGHT_VIEW_CONTACT_INFO)

    if user_rights.exists():
        return True
    return False


def check_admin_approve_right(user, community):

    user_rights = userAdminRights.objects.filter(user=user, community=community,
                                                 state=manager_rights.MANAGER_RIGHT_APPROVE_REMOVE_MEMBERS)

    if user_rights.exists():
        return True
    return False


def check_admin_view_contact_right(user, community):

    user_rights = userAdminRights.objects.filter(user=user, community=community,
                                                 state=manager_rights.MANAGER_RIGHT_DELETE_ROOMS)

    if user_rights.exists():
        return True
    return False


def check_admin_edit_community_right(user, community):

    user_rights = userAdminRights.objects.filter(user=user, community=community,
                                                 state=manager_rights.MANAGER_RIGHT_EDIT_COMMUNITY)

    if user_rights.exists():
        return True
    return False


def get_moderation_history_title(moderation_history):

    user_id = moderation_history.moderation_by.id
    user_name = moderation_history.moderation_by.userinfo.name
    community_id = moderation_history.community.id
    title = None
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

    title = title + f"<{user_name}>|route://member_profile/<{user_id}?community_id={community_id}&member_id={user_id}"

    history = {"title": title, "moderation_time": moderation_history.moderation_time}

    return history


def save_moderation_history(user, community, moderation_by, type):
    """ function to save moderation history """
    moderationHistory(user=user, community=community, moderation_by=moderation_by, type=type).save()


def check_member_invite_private_right(user, community):

    user_rights = userMemberRights.objects.filter(user=user, community=community,
                                                  state=member_rights.MEMBER_RIGHT_INVITE_PRIVATE_LINK)

    if user_rights.exists():
        return True
    return False


def check_member_respond_right(user, community):

    user_rights = userMemberRights.objects.filter(user=user, community=community,
                                                  state=member_rights.MEMBER_RIGHT_RESPOND_IN_ROOM)

    if user_rights.exists():
        return True
    return False


def check_member_create_room_right(user, community):

    user_rights = userMemberRights.objects.filter(user=user, community=community,
                                                  state=member_rights.MEMBER_RIGHT_CREATE_ROOMS)

    if user_rights.exists():
        return True
    return False


def remove_member_auto_approve_right(user, community):

    user_rights = userMemberRights.objects.filter(user=user, community=community,
                                                  state=member_rights.MEMBER_RIGHT_CREATE_ROOMS)

    if user_rights.exists():
        return True
    return False


def give_member_auto_approve_right(user, community):

    user_rights = userMemberRights.objects.filter(user=user, community=community,
                                                  state=member_rights.MEMBER_RIGHT_CREATE_ROOMS)

    if not user_rights.exists():
        user_rights = userMemberRights(user=user, community=community,
                                       state=member_rights.MEMBER_RIGHT_CREATE_ROOMS)
        user_rights.save()

