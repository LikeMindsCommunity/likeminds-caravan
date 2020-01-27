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
        result = time.localtime(int(kwargs['date_time']))

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

        periodic_task = PeriodicTask(
                        name=str(kwargs['task_name']) if 'task_name' in kwargs else None,
                        task=str(kwargs['task_path']) if 'task_path' in kwargs else None,
                        interval=interval,
                        crontab=crontab[0],
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
        periodic_task = PeriodicTask.object.filter(name=task_name)
        periodic_task.update(enabled=False)

    def resume_task(self, task_name):
        """starts the task"""
        periodic_task = PeriodicTask.objects.filter(name=task_name)
        periodic_task.update(enabled=True)

    def terminate_task(self, task_name):
        ''' function to delete the periodic task '''
        periodic_task = PeriodicTask.object.filter(name=task_name)
        periodic_task.delete()

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


