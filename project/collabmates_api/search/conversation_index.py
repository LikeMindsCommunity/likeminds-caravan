from django.conf import settings

from elasticsearch_dsl import analyzer, token_filter
from django_elasticsearch_dsl_drf.compat import StringField
from django_elasticsearch_dsl import (Document, Index, fields, KeywordField,
                                      BooleanField, IntegerField, TextField, LongField)

from .index_utilities import IndexUtilities

from togther.models import card_answers
from utility.states import conversation_states


# Name of the Elasticsearch index
INDEX = Index(settings.ELASTICSEARCH_INDEX_NAMES[__name__])

# See Elasticsearch Indices API reference for available settings
INDEX.settings(
    number_of_shards=1,
    number_of_replicas=1
)

length_filter = token_filter(
    'keyword_max_length_truncate',
    type="truncate",
    length=10000
)

html_strip = analyzer(
    'html_strip',
    tokenizer="standard",
    filter=["lowercase", "stop", "snowball", length_filter],
    char_filter=["html_strip"]
)

ngram_tokenizer = token_filter(
    'ngram_tokenizer',
    type="ngram",
    min_gram=1,
    max_gram=20,
    token_chars=["letter", "digit"]
)

ngram_analyzer = analyzer(
    "ngram_completion",
    tokenizer="ngram_tokenizer",
    filter=["lowercase"]
)


@INDEX.doc_type
class ConversationDocument(Document):
    """Conversation Elasticsearch document."""

    id = IntegerField()
    answer = TextField(
        analyzer=html_strip,
        fields={
            'raw': KeywordField(),
            'lower': TextField(analyzer=html_strip)
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
            'date_epoch': LongField(),
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
