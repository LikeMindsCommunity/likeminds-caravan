from django import  forms
from togther.models import *

class CommunityForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(CommunityForm, self).__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['about'].required = False
        self.fields['purpose'].required = True
        self.fields['location'].required = False
        self.fields['image_url'].required = False
        self.fields['hide_community'].required = False
        self.fields['introduction_text_state'].required = True

    class Meta:
        model=Community
        fields=['name','about','purpose','location','hide_community','introduction_text_state','image_url']
        attrs = {'class': 'form-control form-group'}
        attr_purpose={'class': 'form-control form-group','minlength':40,'placeholder':'For'}
        attr_hidden={'class': 'form-control form-group','minlength':1,'placeholder':'Enter 1 to hide,0 to unhide and 2 to delete'}
        attr_introduction_text={'class': 'form-control form-group','placeholder':'Enter 1 to disable Introduction Text 0 to Enable Introduction Text'}

        widgets = {
            'name': forms.TextInput(attrs=attrs),
            'about':forms.Textarea(attrs={'cols': 70, 'rows': 10}),
            'purpose':forms.TextInput(attrs=attr_purpose),
            'location':forms.TextInput(attrs=attrs),
            'hide_community': forms.TextInput(attrs=attr_hidden),
            'introduction_text_state': forms.TextInput(attrs=attr_introduction_text),
            'image_url':forms.FileInput(attrs=({'class':'file-upload btn btn-primary'}))
        }


class AdminForm(forms.Form):

    email=forms.EmailField(label='email', widget=forms.TextInput(attrs={'placeholder': 'Email' ,'class':'form-control form-group'}))



class MemberForm(forms.Form):

    email=forms.EmailField(label='email', widget=forms.TextInput(attrs={'placeholder': 'Email' ,'class':'form-control form-group'}))





class UserForm(forms.ModelForm):


    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['city'].required = False
        self.fields['contact_number'].required = False
        self.fields['interests'].required = False
        self.fields['fb_link'].required = False
        self.fields['linkedin_link'].required = False
        self.fields['fcm_token'].required = False
        self.fields['image_file'].required = False

    class Meta:
        model=Userinfo
        fields=['name','city','contact_number','interests','fb_link','linkedin_link','fcm_token','login_type','image_file']
        attrs = {'class': 'form-control form-group'}
        attr_purpose={'class': 'form-control form-group','minlength':40}
        widgets = {
            'name': forms.TextInput(attrs=attrs),
            'city':forms.TextInput(attrs=attrs),
            'contact_number':forms.TextInput(attrs=attrs),
            'interests':forms.TextInput(attrs=attrs),
            'fb_link':forms.TextInput(attrs=attrs),
            'linkedin_link':forms.TextInput(attrs=attrs),
            'fcm_token':forms.TextInput(attrs=attrs),
            'login_type':forms.TextInput(attrs=attrs),
            'image_file': forms.FileInput(attrs=({'class': 'file-upload btn btn-primary'}))
        }

class SendNominatedEmail(forms.Form):

    proposer_name=forms.CharField(label='proposer_name', widget=forms.TextInput(attrs={'placeholder': 'Person who nomitate' ,'class':'form-control form-group'}))
    proposer_email=forms.EmailField(label='proposer_email', widget=forms.TextInput(attrs={'placeholder': 'Email' ,'class':'form-control form-group'}))

    proposed_name=forms.CharField(label='proposed_name', widget=forms.TextInput(attrs={'placeholder': 'Person who is nominted' ,'class':'form-control form-group'}))
    proposed_email=forms.EmailField(label='proposed_email', widget=forms.TextInput(attrs={'placeholder': 'Email' ,'class':'form-control form-group'}))
    proposed_no=forms.CharField(required=False,label='Contact no', widget=forms.TextInput(attrs={'placeholder': 'Optional' ,'class':'form-control form-group'}))




class Tester_mail_form(forms.Form):

    name=forms.CharField(label='name',widget=forms.TextInput(attrs={'placeholder':'Name of person who recievs mail','class':'form-control form-group'}))
    email=forms.EmailField(label='email', widget=forms.TextInput(attrs={'placeholder': 'Email' ,'class':'form-control form-group'}))


class Legacy_Education_Form(forms.Form):
    demonym = forms.CharField(label='Demonym',max_length=500,required=False,widget=forms.TextInput(attrs={'placeholder':'Demonym','class':'form-control form-group'}))
    short_name = forms.CharField(label='Short Name',max_length=500,required=False,widget=forms.TextInput(attrs={'placeholder':'Short Name','class':'form-control form-group'}))
    image = forms.ImageField(label='Select Image',required=False,widget=forms.FileInput(attrs=({'class': 'file-upload btn btn-primary'})))


class Legacy_Hometown_Form(forms.Form):
    home_demonym = forms.CharField(label='Demonym', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'Natives of','class':'form-control form-group'}))
    image = forms.ImageField(label='Select Image', required=False,widget=forms.FileInput(attrs=({'class': 'file-upload btn btn-primary'})))


class Profession_Skill_Form(forms.Form):

    skill_name = forms.CharField(label='Skill Name', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'Skill Name','class':'form-control form-group'}))
    skill_experts = forms.CharField(label='Skill Experts', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'Skill Experts','class':'form-control form-group'}))
    image = forms.ImageField(label='Select Image', required=False,widget=forms.FileInput(attrs=({'class': 'file-upload btn btn-primary'})))


class Profession_Industry_Form(forms.Form):
    #demonym = forms.CharField(label='Demonym', max_length=50, required=False,widget=forms.TextInput(attrs={'placeholder':'Demonym','class':'form-control form-group'}))
    industry_name = forms.CharField(label='Industry Name', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'Industry Name','class':'form-control form-group'}))
    image = forms.ImageField(label='Select Image', required=False,widget=forms.FileInput(attrs=({'class': 'file-upload btn btn-primary'})))



class Interests_Cause_Form(forms.Form):
    thing_event = forms.CharField(label='Thing Event', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'discussion or event','class':'form-control form-group'}))
    image = forms.ImageField(label='Select Image', required=False,widget=forms.FileInput(attrs=({'class': 'file-upload btn btn-primary'})))


class Interests_Hobby_Form(forms.Form):

    hobby_name = forms.CharField(label='Hobby Name', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'Hobby Name','class':'form-control form-group'}))
    hobbyists = forms.CharField(label='Hobbyists', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'Hobbyists','class':'form-control form-group'}))
    hobby_group_used_case = forms.CharField(label='Hobby Group Used Case', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'Hobby Group Used Case','class':'form-control form-group'}))
    hobby_group_event = forms.CharField(label='Hobby Group Event', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'Hobby Group Event','class':'form-control form-group'}))
    hobby_event = forms.CharField(label='Hobby Event', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'Hobby Event','class':'form-control form-group'}))
    image = forms.ImageField(label='Select Image', required=False,widget=forms.FileInput(attrs=({'class': 'file-upload btn btn-primary'})))


class Interests_Sports_Form(forms.Form):
    sport_players = forms.CharField(label='Sport Players', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'Sport enthusiasts','class':'form-control form-group'}))
    sport_usecase = forms.CharField(label='Sport usecase', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'play the sport','class':'form-control form-group'}))
    sport_event = forms.CharField(label='Sport event', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'match','class':'form-control form-group'}))
    image = forms.ImageField(label='Select Image', required=False,widget=forms.FileInput(attrs=({'class': 'file-upload btn btn-primary'})))


class Interests_Fan_Form(forms.Form):

    thing = forms.CharField(label='Thing', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'Thing','class':'form-control form-group'}))
    #thing_fan_group_name = forms.CharField(label='Thing Fan Group Name', max_length=50, required=False,widget=forms.TextInput(attrs={'placeholder':'Thing Fan Group Name','class':'form-control form-group'}))
    thing_fans = forms.CharField(label='Thing Fans', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'Thing Fans','class':'form-control form-group'}))
    thing_group_use_case = forms.CharField(label='Thing Group Use Case', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'Thing Group Use Case','class':'form-control form-group'}))
    thing_event = forms.CharField(label='Thing Event', max_length=500, required=False,widget=forms.TextInput(attrs={'placeholder':'Thing Event','class':'form-control form-group'}))
    image = forms.ImageField(label='Select Image', required=False,widget=forms.FileInput(attrs=({'class': 'file-upload btn btn-primary'})))

class Geography_Form(forms.Form):
    demonym = forms.CharField(label='Demonym',max_length=500,required=False,widget=forms.TextInput(attrs={'placeholder':'Demonym','class':'form-control form-group'}))
    image = forms.ImageField(label='Select Image',required=False,widget=forms.FileInput(attrs=({'class': 'file-upload btn btn-primary'})))



class Tag_Form(forms.Form):

    image = forms.ImageField(label='Select Image', required=False,widget=forms.FileInput(attrs=({'class': 'file-upload btn btn-primary'})))


class Tag_Rank_Form(forms.ModelForm):


    class Meta:
        model=Tags_lpig
        fields=['tag_rank']
        attrs = {'class': 'form-control form-group'}


        widgets = {
           'tag_rank':forms.TextInput(attrs=attrs)
        }

