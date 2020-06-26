import xlrd
from togther.models import communityFieldTypes,communityFieldSubTypes,communityField
import re
import time
from .static import *
import json
def get_type_of_community():

    loc = ("scripts/test.xlsx")

    wb = xlrd.open_workbook(loc)
    sheet = wb.sheet_by_index(0)

    sheet.cell_value(0, 0)
    result = []
    print("--------========----------==========---------==========--------===========")
    for row in range(2, sheet.nrows):
        temp = {}
        type = sheet.cell_value(row, 0)
        temp['type'] = type
        temp['subtype'] = sheet.cell_value(row,1)
        temp['profile_link'] = sheet.cell_value(row,2)
        temp['ms1'] = sheet.cell_value(row,3)
        temp['ms2'] = sheet.cell_value(row,4)
        temp['ms3'] = sheet.cell_value(row,5)
        temp['s1'] = sheet.cell_value(row,6)
        temp['s2'] = sheet.cell_value(row,7)
        temp['s3'] = sheet.cell_value(row, 8)
        temp['s4'] = sheet.cell_value(row,9)

        temp['short'] = sheet.cell_value(row,10)
        temp['introduction'] = sheet.cell_value(row,11)
        temp['help_text'] = sheet.cell_value(row,12)
        temp['mcq'] = sheet.cell_value(row,17)

        result.append(temp)
        break




    for field in result:

        #geting profile link

        field['profile_link'] = field['profile_link'].split(",")
        field['ms1'] = get_field_data(field['ms1'])
        field['ms2'] = get_field_data(field['ms2'])
        field['s1'] = get_field_data(field['s1'])
        field['s2'] = get_field_data(field['s2'])
        field['s3'] = get_field_data(field['s3'])
        field['s4'] = get_field_data(field['s4'])
        field['short'] = get_field_data(field['short'])
        field['introduction'] = get_field_data(field['introduction'])
        field['help_text'] = get_field_data(field['help_text'])
        field['mcq'] = get_field_data(field['mcq'])






def get_field_data(field):

    temp = {}
    temp['field'] = get_pattern_match("""\&&.*?\&&""", field, "&&")
    temp['help_text'] = get_pattern_match("""\##.*?\##""", field, "##")
    temp['options'] = get_pattern_match("""\$#.*?\$#""", field, "$#")
    temp['optional'] =  get_pattern_match("""\$&.*?\$&""", field, "$&")
    return temp



def get_pattern_match(pattern,string,delimeter):

    if not string:
        return ""

    ans = re.search(pattern,string)
    if ans:

        ans = ans.group().replace(delimeter,'')

        return ans

    return ans



def get_bussiness_networking():

    '''function to get bussiness networking data'''

    loc = ("scripts/bussiness_networking.xlsx")

    wb = xlrd.open_workbook(loc)
    sheet = wb.sheet_by_index(1)

    sheet.cell_value(0, 0)
    result = []
    print("--------========----------==========---------==========--------===========")
    for row in range(3, sheet.nrows):
        temp = {}
        # type = sheet.cell_value(row, 0)
        # temp['type'] = type

        temp['subtype'] = sheet.cell_value(row, 0)
        temp['profile_link'] = sheet.cell_value(row, 1)

        temp['ms1'] = sheet.cell_value(row, 2)
        temp['ms2'] = sheet.cell_value(row, 3)
        temp['ms3'] = sheet.cell_value(row, 4)
        temp['ms4'] = sheet.cell_value(row, 5)

        temp['s1'] = sheet.cell_value(row, 6)
        temp['s2'] = sheet.cell_value(row, 7)
        temp['s3'] = sheet.cell_value(row, 8)
        temp['s4'] = sheet.cell_value(row, 9)

        temp['introduction'] = sheet.cell_value(row, 10)
        temp['short-3'] = sheet.cell_value(row, 11)

        temp['short-1'] = sheet.cell_value(row,12)
        temp['short-2'] = sheet.cell_value(row,13)

        temp['mcq-1'] = sheet.cell_value(row, 18)
        temp['mcq-2'] = sheet.cell_value(row, 18)
        result.append(temp)



    field_list = []
    for field in result:

        #geting profile link

        field['profile_link'] = field['profile_link'].split(",")

        field['ms1'] = get_field_data(field['ms1'])
        field['ms2'] = get_field_data(field['ms2'])
        field['ms3'] = get_field_data(field['ms3'])
        field['ms4'] = get_field_data(field['ms4'])

        field['s1'] = get_field_data(field['s1'])
        field['s2'] = get_field_data(field['s2'])
        field['s3'] = get_field_data(field['s3'])
        field['s4'] = get_field_data(field['s4'])

        field['short-1'] = get_field_data(field['short-1'])
        field['short-2'] = get_field_data(field['short-2'])

        field['introduction'] = get_field_data(field['introduction'])
        field['short-3'] = get_field_data(field['short-3'])

        field['mcq-1'] = get_field_data(field['mcq-1'])
        field['mcq-2'] = get_field_data(field['mcq-2'])


        field_list.append(field)


    return field_list

def create_dropdown_field(data,subtype,state,field=True):

    type_instance = communityFieldTypes.objects.get(id=1)
    subtype_instance = communityFieldSubTypes.objects.get(sub_type=subtype)

    if not data['field']:
        return



    field_filter = communityField.objects.filter(type=type_instance,sub_type=subtype_instance,question_title=data['field'],state=state)

    if not field_filter.exists():
        instance = communityField()

        instance.type = type_instance
        instance.sub_type = subtype_instance

        instance.question_title = data['field']
        instance.state = state
        instance.value = get_option_data(data['field'],data['options'])
        instance.optional= True if data['optional'] == "true" else False
        instance.help_text = data['help_text']
        instance.field = field
        instance.save()

        print(data['field']+" added")

def create_profile_link(profile_field,subtype):

    type_instance = communityFieldTypes.objects.get(id=1)
    subtype_instance = communityFieldSubTypes.objects.get(sub_type=subtype)

    for profile in profile_field:
        if profile:
            profile = profile.strip()
            value_list = [{"profile_platform":profile,"answer_privacy":"Public"}]
            field_filter = communityField.objects.filter(type=type_instance, sub_type=subtype_instance,question_title=profile,state=8)
            if not field_filter:
                instance = communityField()
                instance.type = type_instance
                instance.sub_type = subtype_instance
                instance.question_title = profile
                instance.state = 8
                instance.optional = False
                instance.help_text = ""
                instance.value = json.dumps(value_list)
                instance.field = True
                instance.save()
            print(profile)

def create_subtype_fields(networking):

    type_instance = communityFieldTypes.objects.get(id=1)
    for data in networking:

        subtype_filter = communityFieldSubTypes.objects.filter(sub_type=data['subtype'], type=type_instance)
        if not subtype_filter.exists():
            instance = communityFieldSubTypes()
            instance.type = type_instance
            instance.sub_type = data['subtype']
            instance.save()



def create_introduction_fields(data,subtype,state,field):


    introduction = data['field']

    type_instance = communityFieldTypes.objects.get(id=1)
    subtype_instance = communityFieldSubTypes.objects.get(sub_type=subtype)

    if not introduction:
        return

    field_filter = communityField.objects.filter(type=type_instance, sub_type=subtype_instance,
                                                 question_title=introduction, state=state)

    value_list = [{"min_chars": "50", "max_chars": "No limit"}]
    if not field_filter.exists():
        instance = communityField()

        instance.type = type_instance
        instance.sub_type = subtype_instance

        instance.question_title = introduction
        instance.state = state
        instance.value = json.dumps(value_list)
        instance.optional = True if data['optional'] == "true" else False
        instance.help_text = ''
        instance.field = field
        instance.save()
        print(data['field']+" added")



def create_short_answer_field(data,subtype,state,field):



    type_instance = communityFieldTypes.objects.get(id=1)
    subtype_instance = communityFieldSubTypes.objects.get(sub_type=subtype)

    if not data['field']:
        return

    field_filter = communityField.objects.filter(type=type_instance, sub_type=subtype_instance,
                                                 question_title=data['field'], state=state)

    if not field_filter.exists():
        instance = communityField()

        instance.type = type_instance
        instance.sub_type = subtype_instance

        instance.question_title = data['field']
        instance.state = state
        instance.value = None
        instance.optional = True if data['optional'] == "true" else False
        instance.help_text = ''
        instance.field = field
        instance.save()
        print(data['field']+" added")



def create_user_created_mcq(data,subtype,state,field=True):

    type_instance = communityFieldTypes.objects.get(id=1)
    subtype_instance = communityFieldSubTypes.objects.get(sub_type=subtype)

    if not data['field']:
        return



    field_filter = communityField.objects.filter(type=type_instance,sub_type=subtype_instance,question_title=data['field'],state=state)

    if not field_filter.exists():
        instance = communityField()

        instance.type = type_instance
        instance.sub_type = subtype_instance

        instance.question_title = data['field']
        instance.state = state
        instance.value = get_option_data(data['field'],data['options'],user_added=True)
        instance.optional= True if data['optional'] == "true" else False
        instance.help_text = data['help_text']
        instance.field = field
        instance.save()
        print(data['field']+" added")


def get_option_data(field,options,user_added=False):


    if field == "College":
       return  json.dumps(COLLEGES)

    if field == "City":
        return json.dumps(CITIES)

    if options == "":
        return
    print(field)


    if field == "School":
        print(field)
        print(options)
        options = options.split("$")

    else:

        options = options.split(",")


    option_list = []

    for option in options:
        temp={}
        temp['value'] = option

        option_list.append(temp)

    if user_added:
        option_list.append({'value':True})

    return json.dumps(option_list)


def create_all_fields(networking):

    for field in networking:
        create_profile_link(field['profile_link'], field['subtype'])
        create_dropdown_field(field['ms1'], field['subtype'], state=2, field=True)
        create_dropdown_field(field['ms2'], field['subtype'], state=2, field=True)
        create_dropdown_field(field['ms3'], field['subtype'], state=2, field=True)
        create_dropdown_field(field['ms4'], field['subtype'], state=2, field=True)

        # single field
        create_dropdown_field(field['s1'], field['subtype'], state=1, field=True)
        create_dropdown_field(field['s2'], field['subtype'], state=1, field=True)
        create_dropdown_field(field['s3'], field['subtype'], state=1, field=True)
        create_dropdown_field(field['s4'], field['subtype'], state=1, field=True)

        # print(field['introduction'])
        # print(field['help_text'])
        # create introduction fields
        create_introduction_fields(field['introduction'], field['subtype'], state=7, field=False)

        create_short_answer_field(field['short-1'], field['subtype'], state=4, field=False)
        create_short_answer_field(field['short-2'], field['subtype'], state=4, field=False)
        create_short_answer_field(field['short-3'], field['subtype'], state=4, field=False)

        create_user_created_mcq(field['mcq-1'], field['subtype'], state=2, field=False)
        create_user_created_mcq(field['mcq-2'], field['subtype'], state=2, field=False)

        print("subtype--------------------------",field['subtype'])



start_time = time.time()

networking = get_bussiness_networking()

create_subtype_fields(networking)


create_all_fields(networking)




end_time = time.time()

diff = end_time - start_time

print(diff)