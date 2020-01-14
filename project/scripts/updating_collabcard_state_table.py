import time
from django.contrib.auth.models import User
from togther.models import *
from utility.states import collabcard_seen_state,collabcard_follow_state


def update_collabcard_state():


    collabcard_list=Collabcard.objects.all().order_by('id')

    user_list=User.objects.all().order_by('id')


    for collabcard in collabcard_list:

        if not is_collabcard_state_present(collabcard, collabcard.user):
            collabcard_state_instance = collabcardState()
            collabcard_state_instance.card = collabcard
            collabcard_state_instance.user = collabcard.user
            collabcard_state_instance.community = collabcard.community
            collabcard_state_instance.state = collabcard_follow_state
            collabcard_state_instance.created_at = time.time()
            collabcard_state_instance.updated_at = time.time()
            collabcard_state_instance.save()
            log="""State saved for user=%s for collabcard_id=%s"""%(str(collabcard.user.userinfo.name),str(collabcard.id))
            print(log)

        for user in user_list:
            state=get_status_of_collabcard(user.id,collabcard.community,collabcard.id)
            if state:
                if not is_collabcard_state_present(collabcard, user):
                    collabcard_state_instance = collabcardState()
                    collabcard_state_instance.card = collabcard
                    collabcard_state_instance.user = user
                    collabcard_state_instance.community = collabcard.community
                    collabcard_state_instance.state = state
                    collabcard_state_instance.created_at = time.time()
                    collabcard_state_instance.updated_at = time.time()
                    collabcard_state_instance.save()
                    log = """State saved for user=%s for collabcard_id=%s""" % (
                    str(user.userinfo.name), str(collabcard.id))
                    print(log)


def is_collabcard_state_present(card_instance,user_instance):

    '''function to check if the detail is already present or not'''
    collabcard_state=collabcardState.objects.filter(card=card_instance,user=user_instance)

    if collabcard_state:
        return True
    return False

def get_status_of_collabcard(member_id,community,card):
    '''function to get the state of collabcard'''
    state=0

    seen_status=collabcard_seen.objects.filter(card=card,community=community,user=member_id)
    if seen_status:
        state=1
        follow=follow_collabcard.objects.filter(collabcard_id=card,member_id=member_id)
        if follow:
            state=2

    return state


start_time=time.time()
update_collabcard_state()
end_time=time.time()

diff=(end_time-start_time)
print(diff)