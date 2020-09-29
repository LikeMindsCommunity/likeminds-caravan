from django.forms import ModelForm

from togther.models import communityFieldTypes,communityFieldSubTypes,communityField

class communityFieldTypesForm(ModelForm):
    class Meta:
        model = communityFieldTypes
        fields = [
            'type',
            'sub_type_header',
            'sub_type_placeholder',
            'rank',
        ]

class communityFieldSubTypesForm(ModelForm):
    class Meta:
        model = communityFieldSubTypes
        fields = [
            'type',
            'sub_type',
            'rank',
        ]

class communityFieldForm(ModelForm):
    class Meta:
        model = communityField
        fields = [
            'type',
            'sub_type',
            'question_title',
            'value',
            'optional',
            'help_text',
            'field',
            'is_compulsory',
        ]