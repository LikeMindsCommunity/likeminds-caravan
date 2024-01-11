from celery import shared_task
from django.apps import apps
from django.db import transaction
from django.conf import settings
from django_elasticsearch_dsl.registries import registry
from django_elasticsearch_dsl.signals import RealTimeSignalProcessor

from project.celery import app

ELASTIC_SEARCH_QUEUE_NAME = settings.ELASTIC_SEARCH_QUEUE_NAME if settings.ELASTIC_SEARCH_QUEUE_NAME else \
    app.conf.task_default_queue


class AsyncElasticSearchIndexBuilder:

    @staticmethod
    @shared_task(queue=ELASTIC_SEARCH_QUEUE_NAME)
    def handle_save(pk, app_label, model_name):
        sender = apps.get_model(app_label, model_name)
        instance = sender.objects.get(pk=pk)
        registry.update(instance)
        registry.update_related(instance)


class CelerySignalProcessor(RealTimeSignalProcessor):
    """Celery signal processor.
    Allows automatic updates on the index as delayed background tasks using
    Celery.
    """

    def handle_save(self, sender, instance, **kwargs):
        """Handle save.

        Given an individual model instance, update the object in the index.
        Update the related objects either.
        """
        app_label = instance._meta.app_label
        model_name = instance._meta.model_name
        transaction.on_commit(
            lambda: AsyncElasticSearchIndexBuilder.handle_save.delay(instance.pk, app_label, model_name)
        )
