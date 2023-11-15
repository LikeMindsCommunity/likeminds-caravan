from django.conf import settings

from elasticsearch_dsl import analyzer, token_filter, tokenizer
from django_elasticsearch_dsl_drf.compat import StringField
from django_elasticsearch_dsl import (Document, Index, fields, KeywordField,
                                      BooleanField, IntegerField, TextField, LongField)

from .index_utilities import IndexUtilities

from togther.models import card_answers
from utility.states import conversation_states


# Max index length
max_index_length = settings.MAX_INDEX_LENGTH_ELASTICSEARCH

# Name of the Elasticsearch index
INDEX = Index(settings.ELASTICSEARCH_INDEX_NAMES[__name__])

# See Elasticsearch Indices API reference for available settings
INDEX.settings(
    number_of_shards=1,
    number_of_replicas=1
)


# creates a reverse index mappings for combinations of words starting from left
# Ref: https://www.elastic.co/guide/en/elasticsearch/guide/current/_index_time_search_as_you_type.html
edge_ngram_completion_filter = token_filter(
    'edge_ngram_completion_filter',
    type="edge_ngram",
    min_gram=1,
    max_gram=20,
)

autocomplete = analyzer(
    'autocomplete',
    tokenizer="standard",
    filter=["lowercase", edge_ngram_completion_filter],
    char_filter=["html_strip"]
)


@INDEX.doc_type
class ConversationDocument(Document):
    """Conversation Elasticsearch document."""

    id = IntegerField()
    answer = TextField(
        analyzer=autocomplete,
        search_analyzer="standard",
        fields={
            'raw': KeywordField(ignore_above=max_index_length),
            'lower': TextField(analyzer=autocomplete)
        }
    )

    state = IntegerField()

    attachment_count = IntegerField()
    attachments_uploaded = BooleanField()

    is_deleted = BooleanField()
    is_edited = BooleanField()

    created_at = LongField()
    last_updated = LongField()

    chatroom = fields.ObjectField(
        attr='card',
        properties={
            'id': IntegerField(),
            'title': TextField(),
            'header': StringField(),
            'type': IntegerField(attr='type'),
            'is_secret': BooleanField(),
            'is_pinned': BooleanField(),
            'is_pending': BooleanField(),
            'is_deleted': BooleanField(),
            'image_count': IntegerField(),
            'pdf_count': IntegerField(),
            'video_count': IntegerField(),
            'audio_count': IntegerField(),
            'attachment_count': IntegerField(),
            'attachments_uploaded': BooleanField(),
            'device_id': TextField(),
            'platform': TextField(),
            'created_at': LongField(attr='date_epoch'),
            'chatroom_image_url': TextField()
        }
    )

    community = fields.ObjectField(properties={
        'id': IntegerField(),
        'name': StringField(),
    })

    member = fields.ObjectField(
        attr='user',
        properties={
            'id': fields.IntegerField(),
            'profile': fields.ObjectField(
                attr='userinfo',
                properties={
                    'name': StringField(),
                }
            )
        }
    )

    attachments = fields.ObjectField()

    def prepare_attachments(self, instance):
        return IndexUtilities(instance).get_attachments()

    def get_queryset(self):
        return super().get_queryset()\
            .filter(remove=None, state__in=[conversation_states.ANSWER, conversation_states.CONVERSATION_POLL])\
            .exclude(is_deleted=True)\
            .select_related('card', 'community')

    class Django(object):
        """Inner nested class Django."""
        model = card_answers  # The model associate with this Document
        queryset_pagination = 50
