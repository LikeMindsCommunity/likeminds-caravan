
from togther.models import Community
from datetime import datetime, time, timedelta
from togther.models import Collabcard, card_answers, Userinfo, Members, collabcardState, MemberPollVotes, userDevices
from .models import *
from project.celery import app
from celery import shared_task
from collabmates_api.notification import send_silent_notification

def show_community_wise_details(community_id, day_a):
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
        # chatroomdstates = collabcardState.objects.filter(user=user_id).filter(created_at__lte=day_1,
        #                                                                       created_at__gte=day_2).filter(
        #     follow_status=True)
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
        if collabcardstates.exists() or conversations.exists() or chatroom.exists():
            active_counter += 1

    # per_day_record.cumulative_communities = community_count
    per_day_record.new_chatrooms = all_rooms.count()

    per_day_record.community = community

    per_day_record.new_cm_chatrooms = room_by_cm
    per_day_record.new_intro_rooms = intro_room.count()

    #subtracting to remove the first message in chatroom
    per_day_record.new_messages = all_messages.count() - all_rooms.count()
    per_day_record.new_intro_room_messages = intro_room_messages.count() - intro_room.count()

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



def get_weekly_records(community,day=1):
    community_id = community.id

    # last_record = PerWeekRecordOverview.objects.all().order_by('id')
    # if last_record.exists():
    #     record = last_record.last()
    #     total_users = record.new_users_cumulative
    # else:
    #     total_users = 0

    per_day_record = PerWeekRecordOverview()
    # communities = NewCommunities.objects.all()
    # community_count = communities.count()
    # community_id = []
    # for community in communities:
    #     community_id.append(community.community_id)

    midnight = datetime.combine(datetime.today(), datetime.min.time())
    # print('^^^',midnight,day*7)
    midnight = midnight - timedelta(days=day*7)
    # print('^^^',midnight)
    day_1 = midnight
    # day_2 = midnight - timedelta(days=day*7)
    day_2 = midnight
    # print('==>',day_1, day_2)

    day_of_week = day_1.weekday()

    day_2 = day_2 + timedelta(days=6-day_of_week+1)

    # day_of_week = day_2.weekday()
    # print(day_2)
    day_1 = day_1 - timedelta(days=day_of_week)
    # print(day_1, day_2)
    # return
    day_1 = day_1.timestamp() + 5*60*60 + 30*60
    day_2 = day_2.timestamp() + 5*60*60 + 30*60

    test_day = day_1 + 60*60



    #get chatroomn data
    intro_room = Collabcard.objects.filter(date_epoch__lte=day_2,date_epoch__gte=day_1).filter(community__id=community_id).filter(type=1)
    all_rooms = Collabcard.objects.filter(date_epoch__lte=day_2,date_epoch__gte=day_1).filter(community__id=community_id)
    room_by_cm = 0
    # for c_id in community_id:
    admins = Members.objects.filter(community_id=community_id, state=1)
    for admin in admins:
        admin_chatroom = all_rooms.filter(user=admin.member_id).filter(community_id=community_id)
        room_by_cm += admin_chatroom.count()


    #get message data
    all_messages = card_answers.objects.filter(created_at__lte=day_2, created_at__gte=day_1).filter(
        card__community__id=community_id)
    intro_room_messages = card_answers.objects.filter(created_at__lte=day_2, created_at__gte=day_1).filter(
        card__community__id=community_id).filter(card__type=1)
    poll_room_messages = card_answers.objects.filter(created_at__lte=day_2, created_at__gte=day_1).filter(
        card__community__id=community_id).filter(card__type=3)
    event_room_messages = card_answers.objects.filter(created_at__lte=day_2, created_at__gte=day_1).filter(
        card__community__id=community_id).filter(card__type=2)


    #acquired users data
    new_users = Userinfo.objects.filter(created_at__lte=day_2,created_at__gte=day_1)


    # members added
    members = Members.objects.filter(created_at__lte=day_2,created_at__gte=day_1).filter(community_id=community_id)
    all_members = Members.objects.filter(community_id=community_id)



    #active members
    all_members = Members.objects.filter(community_id=community_id,state__in=[1,4]).values('member_id').distinct()
    active_counter = 0
    for m in all_members:
        user_id = m['member_id']
        # chatroomdstates = collabcardState.objects.filter(user=user_id).filter(created_at__lte=day_1,
        #                                                                       created_at__gte=day_2).filter(
        #     follow_status=True)
        collabcardstates = collabcardState.objects.filter(user=user_id).filter(created_at__lte=day_2,
                                                                               created_at__gte=day_1).filter(
            follow_status=True).filter(card__community__id=community_id)
        conversations = card_answers.objects.filter(user=user_id).filter(created_at__lte=day_2,
                                                                         created_at__gte=day_1).filter(
            card__community__id=community_id)
        chatroom = Collabcard.objects.filter(user=user_id).filter(date_epoch__lte=day_2, date_epoch__gte=day_1).filter(
            community__id=community_id)
        # votes = MemberPollVotes.objects.filter(user=user_id).filter(created_at__lte=day_1,
        #                                                             created_at__gte=day_2).filter(
        #     card__community__id=community_id)
        if collabcardstates.exists() or conversations.exists() or chatroom.exists():
            active_counter += 1

    # per_day_record.cumulative_communities = community_count
    per_day_record.new_chatrooms = all_rooms.count()
    per_day_record.community = community
    per_day_record.new_cm_chatrooms = room_by_cm
    per_day_record.new_intro_rooms = intro_room.count()

    #subtracting to remove the first message in chatroom
    per_day_record.new_messages = all_messages.count() - all_rooms.count()
    per_day_record.new_intro_room_messages = intro_room_messages.count() - intro_room.count()

    per_day_record.new_intro_poll_messages = poll_room_messages.count()
    per_day_record.new_intro_event_messages = event_room_messages.count()
    per_day_record.new_messages_by_cm = 0
    per_day_record.new_users = new_users.count()
    # per_day_record.new_users_cumulative = new_users.count() + total_users
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

    if datetime.today().weekday() == 0:
        run_weekly_tasks()


def run_weekly_tasks(day=1):
    communities = Community.objects.filter(created_at__gte=1596157200)
    for community in communities:
        get_weekly_records(community,day)



def sanitize_division(a,b):
    if b == 0:
        return '-'
    else:
        return ("%.2f" % (a/b))

def get_percent(a,b):
    if b == 0:
        return '-'
    else:
        return ("%.0f" % (a/b*100) + '%')


@app.task
def find_uninstall_devices():
    """
    task to be run at 3 am to check if user has app installed
    """
    user_devices = userDevices.objects.all()
    all_users = User.objects.all()

    for user in all_users:
        app_uninstall, created = appUninstalls.objects.get_or_create(user=user)

        #skip the user  if the uninstall days == 10
        if app_uninstall.uninstall_days == 10:
            continue

        devices = user_devices.filter(user=user)
        flag_installed = False
        token_list = get_user_tokens(devices)

        if len(token_list):
            result = send_silent_notification(token_list)

            if result['success'] > 0:
                flag_installed = True

        if flag_installed:
            app_uninstall.uninstall_days = 0
        else:
            app_uninstall.uninstall_days = app_uninstall.uninstall_days + 1

        app_uninstall.save()


def get_user_tokens(devices):
    token_list = []
    for device in devices:
        token_list.append(device.fcm_token)
    return token_list
