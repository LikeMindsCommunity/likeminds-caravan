import xlrd
from togther.models import communityType,communitySubtype,masterQuestions
from utility.states import question_states
import time
import json
def get_type_of_community():

    loc = ("scripts/community_questions.xlsx")

    wb = xlrd.open_workbook(loc)
    sheet = wb.sheet_by_index(0)

    # For row 0 and column 0
    sheet.cell_value(0, 0)
    typ_set = set()
    type_list=[]
    for row in range(1, sheet.nrows):
        temp={}
        cell= sheet.cell_value(row, 0)
        sub_cell=sheet.cell_value(row,1)

        if cell and cell not in typ_set:
            temp['type']=cell
            temp['sub_type']=sub_cell
            type_list.append(temp)
        # temp['next_input']=sheet.cell_value(row,2)
        # temp['introduction'] = sheet.cell_value(row, 3)
        # temp['introduction_help'] = sheet.cell_value(row, 4)
        # temp['text1'] = sheet.cell_value(row, 5)
        # temp['text2'] = sheet.cell_value(row, 6)
        # temp['calender'] = sheet.cell_value(row, 7)
        # temp['profile_link']=sheet.cell_value(row,8)
        # temp['multi-select1']=sheet.cell_value(row,9)
        # temp['multi-select2']=sheet.cell_value(row,10)
        # temp['multi-select3']=sheet.cell_value(row,11)
        # temp['single_select']=sheet.cell_value(row,12)


        typ_set.add(cell)

    return type_list


def insert_type_of_community():

    '''function to insert type of community'''

    typ_list=get_type_of_community()
    print(typ_list)
    for typ in typ_list:
        check_data=communityType.objects.filter(typ=typ['type'],next_input_title=typ['sub_type'])

        if not check_data:
            type_instance=communityType()
            type_instance.typ=typ['type']
            type_instance.next_input_title=typ['sub_type']
            type_instance.save()

    print("Data inserted successfully")




def create_question(question_title,sub_type,typ,state,help_text=None,value=None):

    '''function to create master question'''

    if not question_title:
        return

    if state  == question_states.CHOICE_SINGLE or state == question_states.CHOICE_MULTIPLE:

        test_string =  send_string_dropdown(question_title)
        question_title = test_string[0]
        value = test_string[1]
        value=json.dumps(value)


    typ_instances=communityType.objects.filter(pk=typ)
    if typ_instances:
        masterQuestions_instance=masterQuestions()
        masterQuestions_instance.question_title=question_title
        masterQuestions_instance.sub_type=sub_type
        masterQuestions_instance.typ=typ_instances[0]
        masterQuestions_instance.help_text=help_text
        masterQuestions_instance.value=value if value != "null" else None
        masterQuestions_instance.state=state
        masterQuestions_instance.save()

def get_community_details(sheet_no,typ):

    '''function to get alumni community'''

    loc = ("scripts/individual_questions.xlsx")

    wb = xlrd.open_workbook(loc)
    sheet = wb.sheet_by_index(sheet_no)
    res_list=[]

    for row in range(1, sheet.nrows):

        temp={}
        temp['type_id']=typ
        temp['next_input']=sheet.cell_value(row,0)
        check_data=communitySubtype.objects.filter(sub_typ=temp['next_input'],typ_id=temp['type_id'])
        if not check_data:
            sub_type_instance=communitySubtype()
            sub_type_instance.sub_typ=temp['next_input']
            sub_type_instance.typ_id=temp['type_id']
            sub_type_instance.save()


            temp['introduction'] = sheet.cell_value(row, 1)
            temp['introduction_help'] = sheet.cell_value(row, 2)

            create_question(temp['introduction'], sub_type_instance,
                            temp['type_id'],question_states.INTRODUCTION,temp['introduction_help'])

            temp['text1'] = sheet.cell_value(row, 3)
            create_question(temp['text1'], sub_type_instance,
                            temp['type_id'], question_states.TEXT)

            temp['text2'] = sheet.cell_value(row, 4)
            create_question(temp['text2'], sub_type_instance,
                            temp['type_id'], question_states.TEXT)

            temp['calender'] = sheet.cell_value(row, 5)
            create_question(temp['calender'], sub_type_instance,
                            temp['type_id'], question_states.DATE_TIME)

            temp['profile_link']=sheet.cell_value(row,6)
            create_question(temp['profile_link'], sub_type_instance,
                            temp['type_id'], question_states.PROFILE_LINK)

            temp['multi-select1']=sheet.cell_value(row,7)
            create_question(temp['multi-select1'], sub_type_instance,
                            temp['type_id'], question_states.CHOICE_MULTIPLE)

            temp['multi-select2']=sheet.cell_value(row,8)
            create_question(temp['multi-select2'], sub_type_instance,
                            temp['type_id'], question_states.CHOICE_MULTIPLE)

            temp['multi-select3']=sheet.cell_value(row,9)
            create_question(temp['multi-select3'], sub_type_instance,
                            temp['type_id'], question_states.CHOICE_MULTIPLE)

            temp['single_select']=sheet.cell_value(row,10)
            create_question(temp['single_select'], sub_type_instance,
                            temp['type_id'], question_states.CHOICE_SINGLE)
        res_list.append(temp)


    return res_list


def send_string_dropdown(test):


    # question = test.split("(")
    index = test.find("?")

    if index != -1:
        question1 = test[:index]

        options_string = test.strip()[index:]
        index = options_string.find("(")
        option = options_string[index:-1]

        option = option.split("$")
        option_list=[]
        for word in option:
            option_list.append({'value':word.strip()})

    else:
        option_list = None
        question1 = test.strip()

    if not option_list:
        option_list = None

    return (question1,option_list)


def updating_communities():


    get_community_details(sheet_no=1,typ=15)
    get_community_details(sheet_no=2, typ=12)
    get_community_details(sheet_no=3, typ=11)
    get_community_details(sheet_no=4, typ=10)
    get_community_details(sheet_no=5, typ=9)
    get_community_details(sheet_no=6, typ=8)
    get_community_details(sheet_no=7, typ=7)
    get_community_details(sheet_no=8, typ=6)
    get_community_details(sheet_no=9, typ=5)
    get_community_details(sheet_no=10, typ=1)

    get_community_details(sheet_no=11, typ=2)
    get_community_details(sheet_no=12, typ=16)
    get_community_details(sheet_no=13, typ=3)
    #get_community_details(sheet_no=14, typ=4)


insert_type_of_community()
time.sleep(2)
updating_communities()
print("Communities Updated")