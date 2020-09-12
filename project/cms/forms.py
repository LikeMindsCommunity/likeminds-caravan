from django.forms import ModelForm

from togther.models import communityType,communitySubtype,communityField

class communityTypeForm(ModelForm):
    class Meta:
        model = communityType
        fields = '__all__'

class communitySubtypeForm(ModelForm):
    class Meta:
        model = communitySubtype
        fields = '__all__'

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