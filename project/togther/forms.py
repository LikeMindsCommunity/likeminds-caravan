from django import forms
from .models import *
from categories import Category_list

class NewGroupForm(forms.ModelForm):
    # category = forms.CharField( max_length=200)
    #category = forms.CharField(label='Category', widget=forms.Select(choices=Category_list))
    class Meta:
        model = Community
        fields = ['name', 'about', 'location', 'image_url']
