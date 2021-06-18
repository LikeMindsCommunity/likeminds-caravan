from django.conf import settings
from django_elasticsearch_dsl import Document, Index, fields, KeywordField, BooleanField, IntegerField, \
    TextField, LongField
from django_elasticsearch_dsl_drf.compat import StringField
from elasticsearch_dsl import analyzer, token_filter

from togther.models import collabcardState
from .index_utilities import IndexUtilities

# Name of the Elasticsearch index
INDEX = Index(settings.ELASTICSEARCH_INDEX_NAMES[__name__])

# See Elasticsearch Indices API reference for available settings
INDEX.settings(
    number_of_shards=1,
    number_of_replicas=1
)

html_strip = analyzer(
    'html_strip',
    tokenizer="keyword",
    filter=["lowercase"],
    char_filter=["html_strip"]
)


@INDEX.doc_type
class ChatroomDocument(Document):
    """Chatroom Elasticsearch document."""

    id = IntegerField(attr='id')

    chatroom = fields.ObjectField(
        attr='card',
        properties={
            'id': IntegerField(),
            'title': TextField(
                analyzer=html_strip,
                fields={
                    'raw': KeywordField(),
                    'lower': TextField(analyzer=html_strip)
                }
            ),
            'header': StringField(
                analyzer=html_strip,
                fields={
                    'raw': KeywordField(),
                    'lower': StringField(analyzer=html_strip)
                }
            ),
            'type': IntegerField(),
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
        },
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

    state = IntegerField()

    mute_status = BooleanField()
    follow_status = BooleanField()
    attending_status = BooleanField()
    is_guest = BooleanField()
    is_tagged = BooleanField()
    secret_chatroom_left = BooleanField()

    updated_at = LongField()

    attachments = fields.ObjectField()

    def prepare_attachments(self, instance):
        return IndexUtilities(instance.card).get_attachments()

    def get_queryset(self):
        return super().get_queryset()\
            .filter(remove=None)\
            .exclude(card__is_deleted=True, secret_chatroom_left=True)\
            .select_related('card', 'community')

    class Django(object):
        """Inner nested class Django."""
        model = collabcardState  # The model associate with this Document
        queryset_pagination = 50
