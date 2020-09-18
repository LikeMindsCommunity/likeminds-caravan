
from togther.models import  Community
from datetime import datetime, time,timedelta
from togther.models import Collabcard
from togther.models import card_answers
from togther.models import Userinfo,Members,collabcardState,MemberPollVotes
from .models import *
from project.celery import app
from celery import shared_task


def show_community_wise_details(community_id,day_a):
    if day_a == 9:
        return
    midnight = datetime.combine(datetime.today(), datetime.min.time())
    day_1 = midnight - timedelta(days=day_a)
    day_2 = midnight - timedelta(days=day_a+1)
    print(day_1,day_2)
    day_1 = day_1.timestamp()
    day_2 = day_2.timestamp()
    communities = Community.objects.filter(id__in=community_id)
    for c in communities:
        print(c.name)
        new_members = Members.objects.filter(created_at__lte=day_1,created_at__gte=day_2).filter(community_id=c.id)
        print(new_members.count())
        print('')
        collabcard_all = Collabcard.objects.filter(date_epoch__lte=day_1,date_epoch__gte=day_2).filter(community=c.id)
        collabcard_intro = Collabcard.objects.filter(date_epoch__lte=day_1,date_epoch__gte=day_2).filter(community=c.id).filter(type=1)
        conversations_all = card_answers.objects.filter(created_at__lte=day_1,created_at__gte=day_2).filter(card__community=c.id)
        converstions_intro = card_answers.objects.filter(created_at__lte=day_1,created_at__gte=day_2).filter(card__community=c.id).filter(card__type=1)
        print(collabcard_all.count())
        print(collabcard_intro.count())
        print(conversations_all.count())
        print(converstions_intro.count())
    show_community_wise_details(day_a+1)




def get_general_records(community,day=0):
    community_id = community.id

    last_record = PerDayRecordOverview.objects.all().order_by('id')
    if last_record.exists():
        record = last_record.last()
        total_users = record.new_users_cumulative
    else:
        total_users = 0

    per_day_record = PerDayRecordOverview()
    # communities = NewCommunities.objects.all()
    # community_count = communities.count()
    # community_id = []
    # for community in communities:
    #     community_id.append(community.community_id)

    midnight = datetime.combine(datetime.today(), datetime.min.time())
    midnight = midnight - timedelta(days=day)
    day_1 = midnight
    day_2 = midnight - timedelta(days=1)
    print(day_1, day_2)

    day_1 = day_1.timestamp() + 5*60*60 + 30*60
    day_2 = day_2.timestamp() + 5*60*60 + 30*60

    test_day = day_1 + 60*60



    #get chatroomn data
    intro_room = Collabcard.objects.filter(date_epoch__lte=day_1,date_epoch__gte=day_2).filter(community__id=community_id).filter(type=1)
    all_rooms = Collabcard.objects.filter(date_epoch__lte=day_1,date_epoch__gte=day_2).filter(community__id=community_id)
    room_by_cm = 0
    # for c_id in community_id:
    admins = Members.objects.filter(community_id=community_id, state=1)
    for admin in admins:
        admin_chatroom = all_rooms.filter(user=admin.member_id).filter(community_id=community_id)
        room_by_cm += admin_chatroom.count()


    #get message data
    all_messages = card_answers.objects.filter(created_at__lte=day_1, created_at__gte=day_2).filter(
        card__community__id=community_id)
    intro_room_messages = card_answers.objects.filter(created_at__lte=day_1, created_at__gte=day_2).filter(
        card__community__id=community_id).filter(card__type=1)
    poll_room_messages = card_answers.objects.filter(created_at__lte=day_1, created_at__gte=day_2).filter(
        card__community__id=community_id).filter(card__type=3)
    event_room_messages = card_answers.objects.filter(created_at__lte=day_1, created_at__gte=day_2).filter(
        card__community__id=community_id).filter(card__type=2)


    #acquired users data
    new_users = Userinfo.objects.filter(created_at__lte=day_1,created_at__gte=day_2)


    # members added
    members = Members.objects.filter(created_at__lte=day_1,created_at__gte=day_2).filter(community_id=community_id)
    all_members = Members.objects.filter(community_id=community_id)



    #active members
    all_members = Members.objects.filter(community_id=community_id).values('member_id').distinct()
    active_counter = 0
    for m in all_members:
        user_id = m['member_id']
        chatroomdstates = collabcardState.objects.filter(user=user_id).filter(created_at__lte=day_1,
                                                                              created_at__gte=day_2).filter(
            follow_status=True)
        collabcardstates = collabcardState.objects.filter(user=user_id).filter(created_at__lte=day_1,
                                                                               created_at__gte=day_2).filter(
            follow_status=True).filter(card__community__id=community_id)
        conversations = card_answers.objects.filter(user=user_id).filter(created_at__lte=day_1,
                                                                         created_at__gte=day_2).filter(
            card__community__id=community_id)
        chatroom = Collabcard.objects.filter(user=user_id).filter(date_epoch__lte=day_1, date_epoch__gte=day_2).filter(
            community__id=community_id)
        # votes = MemberPollVotes.objects.filter(user=user_id).filter(created_at__lte=day_1,
        #                                                             created_at__gte=day_2).filter(
        #     card__community__id=community_id)
        if collabcardstates.exists() or conversations.exists() or chatroom.exists() or chatroomdstates.exists():
            active_counter += 1

    # per_day_record.cumulative_communities = community_count
    per_day_record.new_chatrooms = all_rooms.count()
    per_day_record.community = community
    per_day_record.new_cm_chatrooms = room_by_cm
    per_day_record.new_intro_rooms = intro_room.count()
    per_day_record.new_messages = all_messages.count()
    per_day_record.new_intro_room_messages = intro_room_messages.count()
    per_day_record.new_intro_poll_messages = poll_room_messages.count()
    per_day_record.new_intro_event_messages = event_room_messages.count()
    per_day_record.new_messages_by_cm = 0
    per_day_record.new_users = new_users.count()
    per_day_record.new_users_cumulative = new_users.count() + total_users
    per_day_record.active_users = active_counter
    per_day_record.members_added = members.count()
    per_day_record.cummulative_members = all_members.count()
    per_day_record.updated_at = test_day
    per_day_record.save()


@app.task
@shared_task
def run_daily_tasks(day=0):
    communities = Community.objects.filter(created_at__gte=1596157200)
    for community in communities:
        get_general_records(community,day)