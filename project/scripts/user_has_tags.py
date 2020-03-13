from togther.models import (Community, User_Legacy,
                            User_Profession, User_Interest,
                            User_Geography, Tags_lpig,
                            Category, Attributes,Userinfo)
from django.contrib.auth.models import User
import time

def update_user_has_tags(userinfo_instance):
    result  = user_onbaord(userinfo_instance.user_id)
    print("has tags ==== ", result)
    userinfo_instance.has_tags = result
    userinfo_instance.save()



def user_onbaord(user_instance):
    ''' checking if user has gone through on-boarding flow or not'''
    user_legacy = User_Legacy.objects.filter(user_id=user_instance).select_related('tags_id')
    user_profession = User_Profession.objects.filter(user_id=user_instance).select_related('tags_id')
    user_interest = User_Interest.objects.filter(user_id=user_instance).select_related('tags_id')
    user_geography = User_Geography.objects.filter(user_id=user_instance).select_related('tags_id')

    # if user does not have any tags , user has to do on-boarding

    first_condition = (user_legacy.exists() and user_geography.exists()) and (user_profession.exists() or user_interest.exists())

    second_condition = (legacy_exists(user_legacy) and geography_exists(user_geography)) and (interest_exists(user_interest) or profession_exists(user_profession))
    print("first condition === ", first_condition)
    #
    print("second_condition === ", second_condition)

    if first_condition:
        if second_condition:
            return True
        return False
    else:
        return False

def legacy_exists(user_legacy):

    condition = not (user_legacy.count() == 1 and user_legacy[0].tags_id.tag_id == 15)
    print("legacy_exists === ",condition)
    return condition

def profession_exists(user_profession):
    condition = not (user_profession.count() == 1 and user_profession[0].tags_id.tag_id == 16)
    print("profession_exists === ", condition)
    return condition

def interest_exists(user_interest):
    condition = not (user_interest.count() == 1 and user_interest[0].tags_id.tag_id == 17)
    print("interest_exists === ", condition)
    return condition

def geography_exists(user_geography):
    condition = not (user_geography.count() == 1 and user_geography[0].tags_id.tag_id == 18)
    print("geography_exists === ", condition)
    return condition

def fill_user_has_tags(user_id=None):

    if user_id:
        update_user_has_tags(Userinfo.objects.get(user_id=user_id))
    else:
        userinfo_queryset = Userinfo.objects.all()

        for userinfo in userinfo_queryset:
            update_user_has_tags(userinfo)

start = time.time()
print("script started ")
# fill_user_has_tags()  # to update all users
fill_user_has_tags(user_id=458) # for testing with one user
print("script ended ")
print("time taken === ",time.time() - start)

