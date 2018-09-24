from django import forms
from .models import *

class NewGroupForm(forms.ModelForm):
    category = forms.CharField( max_length=200)
    
    class Meta:
        model = Community
        fields = ['name', 'about', 'location', 'image_url', 'category']