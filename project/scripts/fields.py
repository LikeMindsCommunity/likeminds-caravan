import xlrd
from togther.models import communityFieldTypes,communityFieldSubTypes,communityField
import re
import time
import json
from .static import *

def get_type_of_community(index):

    loc = ("scripts/50k.xlsx")

    wb = xlrd.open_workbook(loc)
    sheet = wb.sheet_by_index(index)

    sheet.cell_value(0, 0)
    type_help_text = sheet.cell_value(1,1)
    subtype_help_text = sheet.cell_value(1,2)
    result = []
    print("--------========----------==========---------==========--------===========")
    for row in range(2, sheet.nrows):
        temp = {}
        type = sheet.cell_value(row, 0)
        temp['type'] = type
        temp['subtype'] = sheet.cell_value(row,1)
        temp['type_help_text'] = type_help_text
        temp['subtype_help_text'] = subtype_help_text

        temp['profile_link'] = sheet.cell_value(row,3)

        temp['ms1'] = sheet.cell_value(row,4)
        temp['ms2'] = sheet.cell_value(row,5)
        temp['ms3'] = sheet.cell_value(row,6)
        temp['ms4'] = sheet.cell_value(row,7)
        temp['ms5'] = sheet.cell_value(row, 8)
        temp['ms6'] = sheet.cell_value(row, 9)
        temp['ms7'] = sheet.cell_value(row, 10)

        temp['date'] = sheet.cell_value(row,11)
        temp['fetch_city_from-1'] =  sheet.cell_value(row,12)
        temp['fetch_city_from-2'] = sheet.cell_value(row, 13)



        temp['s1'] = sheet.cell_value(row,14)
        temp['s2'] = sheet.cell_value(row,15)
        temp['s3'] = sheet.cell_value(row,16)
        temp['s4'] = sheet.cell_value(row,17)
        temp['s5'] = sheet.cell_value(row,18)


        temp['introduction'] = sheet.cell_value(row,19)
        temp['help_text'] = sheet.cell_value(row,20)


        temp['short-1'] = sheet.cell_value(row, 21)
        temp['short-2'] = sheet.cell_value(row, 22)
        temp['short-3'] = sheet.cell_value(row, 23)

        temp['mcq-1'] = sheet.cell_value(row, 24)
        temp['mcq-2'] = sheet.cell_value(row, 25)
        temp['mcq-3'] = sheet.cell_value(row, 26)
        temp['mcq-4'] = sheet.cell_value(row, 27)


        result.append(temp)






    for field in result:

        #geting profile link

        field['profile_link'] = field['profile_link'].split(",")

        field['ms1'] = get_field_data(field['ms1'])
        field['ms2'] = get_field_data(field['ms2'])

        field['ms3'] = get_field_data(field['ms3'])
        field['ms4'] = get_field_data(field['ms4'])
        field['ms5'] = get_field_data(field['ms5'])
        field['ms6'] = get_field_data(field['ms6'])
        field['ms7'] = get_field_data(field['ms7'])



        field['s1'] = get_field_data(field['s1'])
        field['s2'] = get_field_data(field['s2'])
        field['s3'] = get_field_data(field['s3'])
        field['s4'] = get_field_data(field['s4'])
        field['s5'] = get_field_data(field['s5'])

        field['date'] = get_field_data(field['date'])
        field['fetch_city_from-1'] =  get_field_data(field['fetch_city_from-1'])
        field['fetch_city_from-2'] = get_field_data(field['fetch_city_from-2'])



        field['introduction'] = get_field_data(field['introduction'])
        field['help_text'] = get_field_data(field['help_text'])


        field['short-1'] =  get_field_data(field['short-1'])
        field['short-2'] =  get_field_data(field['short-2'])
        field['short-3'] = get_field_data(field['short-3'])

        field['mcq-1'] =  get_field_data(field['mcq-1'])
        field['mcq-2'] =  get_field_data(field['mcq-2'])
        field['mcq-3'] =  get_field_data(field['mcq-3'])
        field['mcq-4'] = get_field_data(field['mcq-4'])




    return result


def create_fieldTypes(networking):


    for field in networking:

        field_filter = communityFieldTypes.objects.filter(type=field['type'])
        if not field_filter.exists():
            type_instance = communityFieldTypes()
            type_instance.type = field['type']
            type_instance.created_at = time.time()
            type_instance.sub_type_header = field['type_help_text']
            type_instance.sub_type_placeholder = field['subtype_help_text']
            type_instance.save()


def create_subtype_fields(networking):



    for data in networking:

        field_filter = communityFieldTypes.objects.filter(type=data['type'])
        if field_filter.exists():
            type_instance = field_filter[0]
            subtype_filter = communityFieldSubTypes.objects.filter(sub_type=data['subtype'], type=type_instance)
            if not subtype_filter.exists():
                instance = communityFieldSubTypes()
                instance.type = type_instance
                instance.sub_type = data['subtype']
                instance.save()



def get_field_data(field):

    temp = {}
    #print(field)
    temp['field'] = get_pattern_match("""\&&.*?\&&""", field, "&&")
    temp['options'] = get_pattern_match("""\##.*?\##""", field, "##")
    temp['help_text'] = get_pattern_match("""\$#.*?\$#""", field, "$#")
    temp['optional'] =  get_pattern_match("""\$&.*?\$&""", field, "$&")
    temp['seprator'] = get_pattern_match("""\%.*\%""",field,"%")


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



def create_dropdown_field(data,type_instance,subtype_instance,state,field=True):

    # type_instance = communityFieldTypes.objects.get(type=field_type)
    # subtype_instance = communityFieldSubTypes.objects.get(sub_type=subtype)


    if not data['field']:
        return



    field_filter = communityField.objects.filter(type=type_instance,sub_type=subtype_instance,question_title=data['field'],state=state)

    if not field_filter.exists():
        instance = communityField()

        instance.type = type_instance
        instance.sub_type = subtype_instance

        instance.question_title = data['field']
        instance.state = state
        instance.value = get_option_data(data,user_added=False)
        instance.optional= True if data['optional'] == "true" else False
        instance.help_text = data['help_text']
        instance.field = field
        instance.save()

        print(data['field']+" added")

def create_profile_link(profile_field,type_instance,subtype_instance):

    # type_instance = communityFieldTypes.objects.get(type=field_type)
    # subtype_instance = communityFieldSubTypes.objects.get(sub_type=subtype)

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


def create_introduction_fields(data,type_instance,subtype_instance,state,field):


    introduction = data['field']

    # type_instance = communityFieldTypes.objects.get(type=field_type)
    # subtype_instance = communityFieldSubTypes.objects.get(sub_type=subtype)

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



def create_short_answer_field(data,type_instance,subtype_instance,state,field):



    # type_instance = communityFieldTypes.objects.filter(type=field_type)
    # subtype_instance = communityFieldSubTypes.objects.get(sub_type=subtype)

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



def create_user_created_mcq(data,type_instance,subtype_instance,state,field=True):

    # type_instance = communityFieldTypes.objects.get(type=field_type)
    # subtype_instance = communityFieldSubTypes.objects.get(sub_type=subtype)

    if not data['field']:
        return



    field_filter = communityField.objects.filter(type=type_instance,sub_type=subtype_instance,question_title=data['field'],state=state)

    if not field_filter.exists():
        instance = communityField()

        instance.type = type_instance
        instance.sub_type = subtype_instance

        instance.question_title = data['field']
        instance.state = state
        instance.value = get_option_data(data,user_added=True)
        instance.optional= True if data['optional'] == "true" else False
        instance.help_text = data['help_text']
        instance.field = field
        instance.save()
        print(data['field']+" added")


def get_option_data(data,user_added=False):


    # if field == "College":
    #    return  json.dumps(COLLEGES)
    #
    # if field == "City":
    #     return json.dumps(CITIES)

    if not data['options']:
        print(data)
        return

    options = data['options']
    field = data['field']



    if data['seprator'] == "dollar":

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

def create_name_email_mobile(title,type_instance,subtype_instance,state,rank,field=False,compulsary=False):

    # type_instance = communityFieldTypes.objects.get(type=field_type)
    # subtype_instance = communityFieldSubTypes.objects.get(sub_type=sub_type)

    if state == 9 or state == 10:
        value_list = [{"answer_privacy":"Private"}]
    else :
        value_list = None

    field_filter = communityField.objects.filter(type=type_instance,sub_type=subtype_instance,question_title=title,state=state)

    if not field_filter.exists():
        instance = communityField()

        instance.type = type_instance
        instance.sub_type = subtype_instance
        instance.question_title = title
        instance.state = state
        instance.value = json.dumps(value_list) if value_list else None
        instance.optional = False
        instance.help_text = ''
        instance.field = field
        instance.rank = rank
        instance.is_compulsory = compulsary
        instance.save()

        print(title)

def create_data_field(data,type_instance,subtype_instance,state,field):


    # type_instance = communityFieldTypes.objects.get(type=field_type)
    # subtype_instance = communityFieldSubTypes.objects.get(sub_type=subtype)

    if not data['field']:
        return

    date_format = [{"date_time":"dd MMM YYYY"}]

    field_filter = communityField.objects.filter(type=type_instance,sub_type=subtype_instance,question_title=data['field'],state=state)

    if not field_filter.exists():
        instance = communityField()

        instance.type = type_instance
        instance.sub_type = subtype_instance

        instance.question_title = data['field']
        instance.state = state
        instance.value = json.dumps(date_format)
        instance.optional= True if data['optional'] == "true" else False
        instance.help_text = data['help_text']
        instance.field = field
        instance.save()



def create_google_city_fetch(data,type_instance,subtype_instance,state,field):


    # type_instance = communityFieldTypes.objects.get(type=field_type)
    # subtype_instance = communityFieldSubTypes.objects.get(sub_type=subtype)

    if not data['field']:
        return



    field_filter = communityField.objects.filter(type=type_instance,sub_type=subtype_instance,question_title=data['field'],state=state)

    if not field_filter.exists():
        instance = communityField()

        instance.type = type_instance
        instance.sub_type = subtype_instance

        instance.question_title = data['field']
        instance.state = state
        instance.value = None
        instance.optional= True if data['optional'] == "true" else False
        instance.help_text = data['help_text']
        instance.field = field
        instance.save()




def create_all_fields(networking):

    for field in networking:


        type_instance = communityFieldTypes.objects.get(type=field['type'])
        subtype_instance = communityFieldSubTypes.objects.get(sub_type=field['subtype'],type=type_instance)

        print("------------------------------type--------------------", field['type'])
        print("------------------------------subtype--------------------",field['subtype'])

        create_profile_link(field['profile_link'], type_instance, subtype_instance)
        create_dropdown_field(field['ms1'], type_instance, subtype_instance, state=2, field=True)

        create_dropdown_field(field['ms2'], type_instance, subtype_instance, state=2, field=True)

        create_dropdown_field(field['ms3'], type_instance, subtype_instance, state=2, field=True)
        create_dropdown_field(field['ms4'], type_instance, subtype_instance, state=2, field=True)
        create_dropdown_field(field['ms5'], type_instance, subtype_instance, state=2, field=True)
        create_dropdown_field(field['ms6'], type_instance, subtype_instance, state=2, field=True)
        create_dropdown_field(field['ms7'], type_instance, subtype_instance, state=2, field=True)

        # single field
        create_dropdown_field(field['s1'], type_instance, subtype_instance, state=1, field=True)
        create_dropdown_field(field['s2'], type_instance, subtype_instance, state=1, field=True)
        create_dropdown_field(field['s3'], type_instance, subtype_instance, state=1, field=True)
        create_dropdown_field(field['s4'], type_instance, subtype_instance, state=1, field=True)
        create_dropdown_field(field['s4'], type_instance, subtype_instance, state=1, field=True)

        create_data_field(field['date'], type_instance, subtype_instance, state=6, field=True)

        create_google_city_fetch(field['fetch_city_from-1'], type_instance, subtype_instance, state=11, field=True)
        create_google_city_fetch(field['fetch_city_from-2'], type_instance, subtype_instance, state=11, field=True)

        create_introduction_fields(field['introduction'], type_instance, subtype_instance, state=7, field=False)

        create_short_answer_field(field['short-1'], type_instance, subtype_instance, state=4, field=False)
        create_short_answer_field(field['short-2'], type_instance, subtype_instance, state=4, field=False)
        create_short_answer_field(field['short-3'], type_instance, subtype_instance, state=4, field=False)

        create_user_created_mcq(field['mcq-1'], type_instance, subtype_instance, state=2, field=False)
        create_user_created_mcq(field['mcq-2'], type_instance, subtype_instance, state=2, field=False)
        create_user_created_mcq(field['mcq-3'], type_instance, subtype_instance, state=2, field=False)
        create_user_created_mcq(field['mcq-4'], type_instance, subtype_instance, state=2, field=False)

        create_name_email_mobile("Name", type_instance, subtype_instance, state=4, rank=3, field=True, compulsary=True)
        create_name_email_mobile("Email", type_instance, subtype_instance, state=10, rank=2, field=True,
                                 compulsary=True)
        create_name_email_mobile("Phone No.", type_instance, subtype_instance, state=9, rank=1, field=True,
                                 compulsary=False)

        print("------------------------------------------------------------------------------------")



def master_field_insert():


    for i in range(0,13):

        networking = get_type_of_community(i)
        create_fieldTypes(networking)
        create_subtype_fields(networking)
        create_all_fields(networking)





def update_fields(update_field,field_value):

    field_filter = communityField.objects.filter(question_title=update_field)

    dump = json.dumps(field_value)
    print(type(dump))
    x = field_filter.update(value=dump)

    print(update_field)
    print(x)


def update_50k_fields():

    update_fields("Colleges", COLLEGES)

    update_fields("Favorite guitarist", COLLEGES)

    update_fields("Birds", BIRDS)

    update_fields("Football clubs", FOOTBALL_CLUBS)

    update_fields("Animated movies", ANIMATED_MOVIES)



def update_help_text():

    loc = ("scripts/50k.xlsx")

    wb = xlrd.open_workbook(loc)
    sheet = wb.sheet_by_index(13)

    print("--------========----------==========---------==========--------===========")
    update_list = []
    for row in range(1, sheet.nrows):

        temp = {}
        temp['id'] = int(sheet.cell_value(row,0))
        temp['help_text'] = sheet.cell_value(row,1)
        update_list.append(temp)


    for data in update_list:


        field_filter = communityField.objects.filter(id=data['id'])

        if field_filter.exists():

            instance = field_filter[0]
            instance.help_text = data['help_text']
            instance.save()
            print("data saved")







start_time = time.time()


update_help_text()

# master_field_insert()
#
#
# update_50k_fields()





end_time = time.time()

diff = end_time - start_time
print(diff)