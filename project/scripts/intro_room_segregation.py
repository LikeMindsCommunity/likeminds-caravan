import time

from django.contrib.auth.models import User

from collabmates_api.views import post_master_introductions_for_community, \
    create_conversation_context_for_intro_chatrooms, post_member_directly_link
from togther.models import Members, Collabcard, collabcardState, Community


def get_all_live_communities():

    community_filter = Members.objects.filter(state=1).order_by('id')

    community_set = set()
    community_list = []

    for community in community_filter:
        community_id = community.community_id.id
        member_id = community.member_id.id

        if community_id not in community_set:
            community_list.append({
                'community_id': community_id,
                'member_id': member_id
            })

            community_set.add(community_id)
    community_list = [{'community_id':49220, 'member_id':496}]
    return community_list


def post_master_intro_cards_in_community():

    community_list = get_all_live_communities()

    for data in community_list:
        community_id = data['community_id']
        member_id = data['member_id']
        post_master_introductions_for_community(community_id, member_id)
        user_instance = User.objects.get(id=member_id)
        community_instance = Community.objects.get(id=community_id)
        post_member_directly_link(user_instance, community_instance)


def set_all_introduction_cards():

    card_filter = Collabcard.objects.filter(type=1).order_by('id')

    for card_instance in card_filter:
        master_intro = Collabcard.objects.filter(type=9,
                                                 community=card_instance.community)
        if master_intro:
            master_intro_instance = master_intro[0]
            create_conversation_context_for_intro_chatrooms(card_instance, card_instance.user, master_intro_instance)
            collabcardState.objects.filter(card=card_instance).update(updated_at=time.time())
            print(card_instance.id)


def intro_room_segregation():

    start_time = time.time()
    post_master_intro_cards_in_community()
    time.sleep(10)
    set_all_introduction_cards()
    end_time = time.time()
    diff = end_time - start_time

    print(diff)


intro_room_segregation()
