from togther.models import *

def set_became_member_at():
    members = Members.objects.all()
    for member in members:
        member.became_member_at = member.updated_at
        member.save()
        print("Member update:",member)


def set_creater_state_for_cr():
    chatrooms = Collabcard.objects.all()
    members = Members.objects.all()
    for chatroom in chatrooms:
        member = members.filter(member_id=chatroom.user,community_id=chatroom.community)
        if member.exists():
            chatroom.member_state = member[0].state
            chatroom.save()
            print("Chatroom updated:",chatroom)

set_creater_state_for_cr()
set_became_member_at()