from togther.models import Community
from datetime import timedelta
from togther.models import Collabcard, card_answers, Userinfo, Members, collabcardState, userDevices
from utility.constants import PLATFORM_CODE_WEB
from .models import *
from project.celery import app
from celery import shared_task
from collabmates_api.notification import send_silent_notification


def show_community_wise_details(community_id, day_a):
    if day_a == 9:
        return
    midnight = datetime.combine(datetime.today(), datetime.min.time())
    day_1 = midnight - timedelta(days=day_a)
    day_2 = midnight - timedelta(days=day_a + 1)
    print(day_1, day_2)
    day_1 = day_1.timestamp()
    day_2 = day_2.timestamp()
    communities = Community.objects.filter(id__in=community_id)
    for c in communities:
        print(c.name)
        new_members = Members.objects.filter(created_at__lte=day_1, created_at__gte=day_2).filter(community_id=c.id)
        print(new_members.count())
        print('')
        collabcard_all = Collabcard.objects.filter(date_epoch__lte=day_1, date_epoch__gte=day_2).filter(community=c.id)
        collabcard_intro = Collabcard.objects.filter(date_epoch__lte=day_1, date_epoch__gte=day_2).filter(
            community=c.id).filter(type=1)
        conversations_all = card_answers.objects.filter(created_at__lte=day_1, created_at__gte=day_2).filter(
            card__community=c.id)
        converstions_intro = card_answers.objects.filter(created_at__lte=day_1, created_at__gte=day_2).filter(
            card__community=c.id).filter(card__type=1)
        print(collabcard_all.count())
        print(collabcard_intro.count())
        print(conversations_all.count())
        print(converstions_intro.count())
    show_community_wise_details(day_a + 1)


def sanitize_division(a, b):
    if b == 0:
        return '-'
    else:
        return ("%.2f" % (a / b))


def get_percent(a, b):
    if b == 0:
        return '-'
    else:
        return ("%.0f" % (a / b * 100) + '%')


@app.task
@shared_task
def find_uninstall_devices():
    """
    task to be run at 3 am to check if user has app installed
    """
    user_devices = ModelUtilities.get_model_filter(userDevices, {})
    all_users = ModelUtilities.get_model_filter(User, {})

    for user in all_users:

        non_web_devices = user_devices.filter(Q(user=user) & (~Q(mobile_os=PLATFORM_CODE_WEB)))
        user_total_devices = user_devices.filter(user=user).count()
        user_web_devices = user_devices.filter(user=user, mobile_os=PLATFORM_CODE_WEB).count()

        if user_total_devices != user_web_devices:
            app_uninstall, created = appUninstalls.objects.get_or_create(user=user)

            # skip the user if the uninstall days == 10
            if app_uninstall.uninstall_days == 10:
                continue

            flag_installed = False
            token_list = get_user_tokens(non_web_devices)

            if len(token_list):
                result = send_silent_notification(token_list)

                if result['success'] > 0:
                    flag_installed = True

            # If all the user related devices are web devices or app is installed
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


def get_error_context(success, error_message):
    return {
        'success': success,
        'error_message': error_message
    }


def raise_custom_exception(response, status):
    raise CustomException(response, status_code=status)
