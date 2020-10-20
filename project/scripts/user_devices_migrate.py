from togther.models import userDevices,Userinfo
import time



def migrate_user_devices():

    '''function to migrate user devices to new table'''

    userinfo_filter = Userinfo.objects.all()

    for data in userinfo_filter:

        devices_filter = userDevices.objects.filter(user=data.user_id, mobile_os=data.mobile_os)
        if not devices_filter.exists() and data.fcm_token:
            instance = userDevices()
            instance.user = data.user_id
            instance.fcm_token = data.fcm_token
            instance.mobile_os = data.mobile_os
            instance.updated_at = time.time()
            instance.save()


start_time = time.time()

migrate_user_devices()

end_time = time.time()

diff = end_time - start_time

print(diff)