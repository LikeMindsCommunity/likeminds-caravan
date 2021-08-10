from django.conf import settings
from django_elasticsearch_dsl import Document, Index, fields, KeywordField, BooleanField, IntegerField, \
    TextField, LongField
from django_elasticsearch_dsl_drf.compat import StringField
from elasticsearch_dsl import analyzer, token_filter

from togther.models import Members

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

# creates a reverse index mappings for combinations of words starting from left
# Ref: https://www.elastic.co/guide/en/elasticsearch/guide/current/_index_time_search_as_you_type.htmlg
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
class MemberDirectoryDocument(Document):
    """Member Directory Elasticsearch document."""

    id = IntegerField(attr='id')

    member = fields.ObjectField(
        attr='member_id',
        properties={
            'id': IntegerField(),
            'user': fields.ObjectField(
                attr='userinfo',
                properties={
                    'name': StringField(
                        analyzer=autocomplete,
                        search_analyzer="standard",
                        fields={
                            'raw': KeywordField(),
                            'lower': StringField(analyzer=autocomplete)
                        }
                    ),
                    'image_url': StringField()
                }
            )
        },
    )

    community_id = fields.ObjectField(
        attr='community_id',
        properties={
            'id': IntegerField(),
            'name': StringField(),
        })

    state = IntegerField()

    created_at = LongField()

    custom_title = TextField(
        analyzer=autocomplete,
        search_analyzer="standard",
        fields={
            'raw': KeywordField(),
            'lower': TextField(analyzer=autocomplete)
        }
    )

    tool_state = IntegerField()
    ask_member_id = IntegerField()
    approved_member_id = IntegerField()
    edit_required = BooleanField()
    actions_required = BooleanField()
    image_url = TextField()

    updated_at = LongField()

    is_owner = BooleanField()
    parent_cm_list = TextField()
    became_member_at = LongField()
    has_onboarded = BooleanField()

    class Django(object):
        """Inner nested class Django."""
        model = Members  # The model associate with this Document
        queryset_pagination = 50
