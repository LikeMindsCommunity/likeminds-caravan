from togther.models import (Members, collabcardState, Userinfo, Collabcard,
                            memberRights, adminRights, userAdminRights, userMemberRights,
                            moderationHistory, Report, Report_Tags)
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
        try:
            userMemberRights(user=user, community=community, right=right).save()
        except:
            pass


def get_saved_member_rights_list(user_rights, admin_rights=None):

    all_member_rights = memberRights.objects.all().order_by("state")
    rights_list = []
    for right in all_member_rights:
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

        if right.sub_title is None:
            del right_dict["sub_title"]

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


def check_all_member_rights(user, community):
    """function to give a manager all the rights """

    admin_rights = userMemberRights.objects.select_related('right').filter(user=user,
                                                                           community=community).order_by("right__state")
    create_room = False
    create_poll = False
    create_event = False
    respond_in_rooms = False
    invite_private = False
    auto_approve = False

    for right in admin_rights:
        right = right.right

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
        elif right.state == auto_approve_member_right['state']:
            auto_approve = True
    rights = {"create_room": create_room, "create_poll": create_poll, "create_event": create_event,
              "respond_in_rooms": respond_in_rooms, "invite_private": invite_private, "auto_approve": auto_approve}

    return rights


def remove_creation_rights_for_user(user, community):
    user_rights = userMemberRights.objects.filter(user=user, community=community).filter(
                                                  Q(right__state=member_rights.MEMBER_RIGHT_CREATE_ROOMS) |
                                                  Q(right__state=member_rights.MEMBER_RIGHT_CREATE_POLL) |
                                                  Q(right__state=member_rights.MEMBER_RIGHT_CREATE_EVENT))
    user_rights.delete()


def check_admin_delete_right(user, community):

    user_rights = userAdminRights.objects.filter(user=user, community=community,
                                                 right__state=manager_rights.MANAGER_RIGHT_VIEW_CONTACT_INFO)

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
                                                 right__state=manager_rights.MANAGER_RIGHT_DELETE_ROOMS)

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

    title = title + f"<{user_name}>|route://member_profile/{user_id}?community_id={community_id}&member_id={user_id}"

    history = {"title": title, "moderation_time": moderation_history.moderation_time}

    return history


def save_moderation_history(user, community, moderation_by, type):
    """ function to save moderation history """
    moderationHistory(user=user, community=community, moderation_by=moderation_by, type=type).save()


def check_member_invite_private_right(user, community):

    user_rights = userMemberRights.objects.filter(user=user, community=community,
                                                  right__state=member_rights.MEMBER_RIGHT_INVITE_PRIVATE_LINK)

    if user_rights.exists():
        return True
    return False


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


def remove_member_create_room_right(user, community):

    create_rights = [member_rights.MEMBER_RIGHT_CREATE_ROOMS, member_rights.MEMBER_RIGHT_CREATE_POLL,
                     member_rights.MEMBER_RIGHT_CREATE_EVENT]
    try:
        userMemberRights.objects.filter(user=user, community=community,
                                        right__state__in=create_rights).delete()
    except:
        print("rights not exists")


def give_member_auto_approve_right(user, community):

    try:
        user_rights = userMemberRights(user=user, community=community,
                                       right__state=member_rights.MEMBER_RIGHT_AUTO_APPROVE)
        user_rights.save()
    except:
        print("right already exists for user ----> ",user.id, community.id, member_rights.MEMBER_RIGHT_AUTO_APPROVE)



def give_member_create_room_right(user, community):

    try:
        user_rights = userMemberRights(user=user, community=community,
                                       right__state=member_rights.MEMBER_RIGHT_CREATE_ROOMS)
        user_rights.save()
    except:
        print("right already exists for user ----> ",user.id, community.id, member_rights.MEMBER_RIGHT_CREATE_ROOMS)


def give_right_to_all_members(community, right):

    community_members = Members.objects.select_related("member_id").filter(community_id=community).exclude(state__in=[3, 5, 6, 8])

    for member in community_members:
        # community_right = userMemberRights.objects.filter(user=member.member_id, community=community, right=right)

        try:
            userMemberRights(user=member.member_id, community=community, right=right).save()
        except:
            print("rights already exists")


def remove_right_for_all_members(community, right):
    userMemberRights.objects.filter(community=community, right=right).delete()



def get_tool_member_requests(user_id, community_id):

    global tool_member_requests
    member_count = Members.objects.filter(community_id=community_id,state=member_states.PENDING_MEMBER).count()
    tool_member_requests = tool_member_requests.copy()
    tool_member_requests["count"] = member_count

    return tool_member_requests


def get_tool_pending_chat_rooms(user_id, community_id):

    global tool_pending_chat_rooms
    count = Collabcard.objects.filter(community_id=community_id, is_pending=True, is_deleted=False).count()
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

    reports = Report.objects.select_related("reported_by", "user_reported", "tag", "action_taken_by",
                                            "action_taken_tag", "community", "collabcard",
                                            "conversation").filter(community=community_id).exclude(type=3).order_by("-id")

    is_owner = kwargs["is_owner"] if "is_owner" in kwargs else False
    parent_cm_list = kwargs["parent_cm_list"] if "parent_cm_list" in kwargs else []
    has_right_0 = kwargs["has_right_0"] if "has_right_0" in kwargs else False
    has_right_1 = kwargs["has_right_1"] if "has_right_1" in kwargs else False
    has_right_2 = kwargs["has_right_2"] if "has_right_2" in kwargs else False
    return_reports_count = kwargs["return_reports_count"] if "return_reports_count" in kwargs else False


    if is_owner:
        # owner cannot see those reports which are reported on owner itself
        reports = reports.exclude(user_reported__id=user_id)

    else:
        reports = reports.exclude(user_reported__id__in=parent_cm_list)
        if has_right_0 and not has_right_1 and not has_right_2:
            # if user has only right 0
            reports = reports.exclude(type=0)
        elif not has_right_1 and not has_right_0 and not has_right_2:
            # if user has only right 1
            reports = reports.exclude(type__in=[1, 2])

    if return_reports_count:
        return reports.count()

    return reports


def get_right_dict(right):

    right_dict = {"id": right.id, "state": right.state, "title": right.title}

    if right.sub_title:
        right_dict["sub_title"] = right.sub_title

    return right_dict




