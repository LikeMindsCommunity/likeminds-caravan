from django import  forms
from crispy_forms.helper import FormHelper
from togther.models import *

class CommunityForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(CommunityForm, self).__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['about'].required = False
        self.fields['purpose'].required = True
        self.fields['location'].required = False
        self.fields['image_url'].required = False
    class Meta:
        model=Community
        fields=['name','about','purpose','location','image_url']
        attrs = {'class': 'form-control form-group'}
        attr_purpose={'class': 'form-control form-group','minlength':40}
        widgets = {
            'name': forms.TextInput(attrs=attrs),
            'about':forms.TextInput(attrs=attrs),
            'purpose':forms.TextInput(attrs=attr_purpose),
            'location':forms.TextInput(attrs=attrs),
            'image_url':forms.FileInput(attrs=({'class':'file-upload btn btn-primary'}))

        }


class AdminForm(forms.Form):

    email=forms.EmailField(label='email', widget=forms.TextInput(attrs={'placeholder': 'Email' ,'class':'form-control form-group'}))



class MemberForm(forms.Form):

    email=forms.EmailField(label='email', widget=forms.TextInput(attrs={'placeholder': 'Email' ,'class':'form-control form-group'}))



