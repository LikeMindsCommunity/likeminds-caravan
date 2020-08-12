from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from datetime import datetime, timedelta
import json
from django.utils import timezone
import time


class CeleryBeatTask:

    def __init__(self):
        return

    def get_or_create_new_beat_task(self,*args,**kwargs):

        # result = time.localtime(time.time()+300)
        date_time = kwargs['date_time'] if "date_time" in kwargs else None
        result = None
        if(date_time):
            result = time.localtime(int(date_time))
            print("result:", result)
            print("\nyear:", result.tm_year)
            print("month:", result.tm_mon)
            print("day:", result.tm_mday)
            print("tm_hour:", result.tm_hour)
            print("tm_min:", result.tm_min)

        interval, created = None, False
        crontab, created = None, False
        if 'interval' in kwargs and kwargs['interval']:
            interval, created = self.get_or_create_interval() if 'interval' in kwargs and kwargs['interval'] else None, False

        if 'crontab' in kwargs and kwargs['crontab']:
            crontab, created = self.get_or_create_crontab(minute=str(result.tm_min),
                                                     hour=str(result.tm_hour),
                                                     day_of_month=str(result.tm_mday),
                                                     month_of_year=str(result.tm_mon)) if 'crontab' in kwargs and kwargs['crontab'] else None, False

        periodic_task = PeriodicTask(
                        name=str(kwargs['task_name']) if 'task_name' in kwargs else None,
                        task=str(kwargs['task_path']) if 'task_path' in kwargs else None,
                        interval=interval[0] if interval else None,
                        crontab=crontab[0] if crontab else None,
                        args=json.dumps(kwargs['args']) if 'args' in kwargs else json.dumps(args) if args else '[]',
                        kwargs=json.dumps(kwargs) if kwargs else '{}',
                        # expires=datetime.utcnow() + timedelta(seconds=30),
                        enabled=True
                        )
        periodic_task.validate_unique()
        periodic_task.save()
        return periodic_task, created


    def get_or_create_crontab(self,**kwargs):
        ''' function to create CrontabSchedule object '''

        crontab, created = CrontabSchedule.objects.get_or_create(
                            minute=str(kwargs['minute']) if 'minute' in kwargs else '*',
                            hour=str(kwargs['hour']) if 'hour' in kwargs else '*',
                            # day_of_week=str(kwargs['week']) if 'week' in kwargs else '*',
                            day_of_month=str(kwargs['day_of_month']) if 'day_of_month' in kwargs else '*',
                            month_of_year=str(kwargs['month_of_year']) if 'month_of_year' in kwargs else '*',
                            timezone='Asia/Kolkata'
                            )
        return crontab, created

    def get_or_create_interval(self,):
        ''' function to create IntervalSchedule object '''
        # choices
        # IntervalSchedule.DAYS
        # IntervalSchedule.HOURS
        # IntervalSchedule.MINUTES
        # IntervalSchedule.SECONDS
        # IntervalSchedule.MICROSECONDS
        interval, created = IntervalSchedule.objects.get_or_create(every=10,
                                    period=IntervalSchedule.SECONDS,
                                    )

        return interval, created



    def stop_task(self, task_name):
        """pauses the task"""
        periodic_task = PeriodicTask.object.get(name=task_name)
        periodic_task.enabled=False
        periodic_task.save()
        print("disabled task succesfully")

    def resume_task(self, task_name):
        """starts the task"""
        periodic_task = PeriodicTask.objects.filter(name=task_name)
        periodic_task.update(enabled=True)

    def terminate_task(self, task_name):
        ''' function to delete the periodic task '''
        periodic_task = PeriodicTask.object.filter(name=task_name)
        periodic_task.delete()
        print("deleted task succesfully")

    def reschedule_task(self, task_name,**kwargs):
        ''' function to reschedule the periodic task '''

        result = time.localtime(int(kwargs['date_time'])+900)

        print("result:", result)
        print("\nyear:", result.tm_year)
        print("month:", result.tm_mon)
        print("day:", result.tm_mday)
        print("tm_hour:", result.tm_hour)
        print("tm_min:", result.tm_min)

        interval, created = self.get_or_create_interval() if 'interval' in kwargs and kwargs['interval'] else None, False
        crontab, created = self.get_or_create_crontab(minute=str(result.tm_min),
                                                 hour=str(result.tm_hour),
                                                 day_of_month=str(result.tm_mday),
                                                 month_of_year=str(result.tm_mon)) if 'crontab' in kwargs and kwargs['crontab'] else None, False

        periodic_task = PeriodicTask.objects.filter(name=task_name)
        periodic_task.update(interval=interval, crontab=crontab)

    def create_dynamic_clery_task(self, args, kwargs, task_name, task_path,
                                  date_time=None, interval=False, crontab=True):
        # example
        # task_name = 'poll_with_id_' + str(kwargs['card_id']) if typ == 3 else 'event_with_id_' + str(
        #     kwargs['card_id'])
        # task_path = 'collabmates_api.notification.poll_expiry_or_event_remainder_notification'
        # args = positional arguments in form of list (should be in exact position as given parameters)
        # kwargs = Extra agruments in form of dictionary in key value pairs

        if task_name and task_path:
            periodic_task, created = self.get_or_create_new_beat_task(args=args, task_name=task_name, task_path=task_path,
                                             date_time=date_time, interval=interval, crontab=crontab,
                                             kwargs=kwargs)
            if(created):
                print("succesfully created dynamic celery beat task")

# uncomment to test


# use this as example
# def create():
#     print("creating celery task hello")
#     celerybeatask = CeleryBeatTask()
#     celerybeatask.create_dynamic_clery_task(args=["hello"],
#                                             kwargs={"first_name": "mahesh", "second_name": " babu"},
#                                             task_name="testing_dynamic_task_creation",
#                                             task_path="utility.celery_beat_tasks.hello",
#                                             interval=True, crontab=False)

# def hello(message,*args,**kwargs):
#     print("message === ", message)
#     print("args === ", args)
#     print("kwargs === ", kwargs)
#     first_name = kwargs["first_name"] if "first_name" in kwargs else "abcd"
#     second_name = kwargs["second_name"] if "second_name" in kwargs else " xyz"
#     print(first_name, second_name)
#
# create()
