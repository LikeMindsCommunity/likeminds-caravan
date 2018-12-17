from django import forms
from .models import *
from categories  import Category_list

class NewGroupForm(forms.ModelForm):
    # category = forms.CharField(label='Category', widget=forms.Select(choices=Category_list))
    category = forms.MultipleChoiceField(
            choices=Category_list,
            initial='0',
            widget=forms.SelectMultiple(attrs={
            'placeholder': 'Additional tags',
            'class': 'ui search fluid dropdown'}),
            required=True,
            label='Category',
        )
    class Meta:
        model = Community
        fields = ['name','purpose','about','category', 'location', 'image_url', 'whatsapp_group_link']
