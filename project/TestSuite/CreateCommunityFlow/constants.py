COMMUNITY_CREATOR = {
    'country_code': 91,
    'mobile_no': 9025253260,
    'type': 'custom',
    'user_acquisition_url': 'likeminds://beta.likeminds.community/community/49289?shared_by=504&aj=84854',
    'user': {
        'image_url': 'https://firebasestorage.googleapis.com/v0/b/collabmates-beta.appspot.com/o/files%2Fprofile%2F9315487184.png?alt=media&token=db5bd903-b8f3-4c42-8058-66859db73e84',
        'name': 'Himanshu Saleria'},
}

CREATE_COMMUNITY_PAGE_1 = {
    'name': 'Rest kro',
    'page': 1,
    'type': 4,
    'sub_type': 31,
    'state': 0,
}

CREATE_COMMUNITY_PAGE_2 = {
    'name': 'Rest kro',
    'page': 2,
    'type': 4,
    'sub_type': 31,
    'state': 0,
    'purpose': 'Rest kro na ho to aansu bhi nahi laga to nhi kr rhi hai aur sabhi se anurodh korbo kivabe use kr rhi '
               'hai kya android phone number of the same hai ab to ye to soho technology thaka or the other day and '
               'night',
    }



DELETE_ROOM = {'id': 1, 'sub_title': None, 'title': 'Delete chat rooms/messages', "state": 0}

APPROVE_MEMBERS = {'id': 2, 'sub_title': None, 'title': 'Approve/remove members', "state": 1}

EDIT_COMMUNITY = {'id': 3, 'sub_title': None, 'title': "Edit community details", "state": 2}

VIEW_CONTACT = {'id': 4, 'sub_title': None, 'title': 'View member contact info', "state": 3}

ADD_MANAGER = {'id': 5, 'sub_title': None, 'title': "Add community managers", "state": 4}

MANAGER_RIGHTS_LIST = [DELETE_ROOM, APPROVE_MEMBERS, EDIT_COMMUNITY, VIEW_CONTACT, ADD_MANAGER]


CREATE_ROOM = {'id': 1, 'sub_title': None, 'title': "Create chat rooms", "state": 0}

CREATE_POLL = {'id': 2, 'sub_title': None, 'title': "Create polls", "state": 1}

CREATE_EVENT = {'id': 3, 'sub_title': None, 'title': "Create events", "state": 2}

RESPOND_IN_ROOMS = {'id': 4, 'sub_title': None, 'title': "Respond in chat rooms", "state": 3}

INVITE_PRIVATE = {'id': 5, 'title': "Invite members via private link",
                  'sub_title': "Private links remain valid for 24 hours and. the user joining via them a re auto verified"
                  , "state": 4
                  }

AUTO_APPROVE_ROOMS = {'id': 6, 'title': "Auto-approve created chat rooms",
                      'sub_title': "If auto-approved, member's chat rooms will be posted instantly and would not need any approval.",
                      "state": 5}

MEMBER_RIGHTS_LIST = [CREATE_ROOM, CREATE_POLL, CREATE_EVENT, RESPOND_IN_ROOMS, INVITE_PRIVATE, AUTO_APPROVE_ROOMS]
