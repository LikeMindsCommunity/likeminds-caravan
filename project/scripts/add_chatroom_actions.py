#script to add chatroom actions in a table

from togther.models import chatroomActions

def add_actions(title_list):


    for title in title_list:

        instance_list = chatroomActions.objects.filter(title=title)

        if not instance_list.exists():

            instance = chatroomActions()
            instance.title = title
            instance.save()

            print(title+" saved with id="+ str(instance.id))




title_list = [
    "Rename chatroom",
    "View participants",
    "Invite",
    "Follow chatroom",
    "View community",
    "Mute notifications",
    "Delete chatroom",
    "Unmute chatroom",
    "Unfollow chatroom"

]

add_actions(title_list)