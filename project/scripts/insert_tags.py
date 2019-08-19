import psycopg2
import xlrd
from connection import get_connection
import json
import time
def read_excell_file():

    loc = ("tags_collabmates.xlsx")

    wb = xlrd.open_workbook(loc)
    sheet = wb.sheet_by_index(0)

    # For row 0 and column 0
    sheet.cell_value(0, 0)

    all_data=[]


    for row in range(1,sheet.nrows):

        if sheet.cell_value(row,6):
            data=sheet.cell_value(row,6)
            data=data+",IIT Delhi"
        else:
            data="IIT Delhi"
        data_dic = {
            'email': sheet.cell_value(row,0),
            'city': sheet.cell_value(row,1),                    #12 4
            'profession_skill': sheet.cell_value(row,2),        #5 2
            'profession_industry': sheet.cell_value(row,3),     #6 2
            'profession_designation':sheet.cell_value(row,4),   #7 2
            'legacy_work':sheet.cell_value(row,5),              #1 1
            'legacy_education':data,         #2 1
            'legacy_hometown':sheet.cell_value(row,7),          #3 1
            'legacy_lifestyle':sheet.cell_value(row,8),         #4 1
            'interest_cause':sheet.cell_value(row,9),           #8 3
            'interest_hobby':sheet.cell_value(row,10),          #9 3
            'interest_sports':sheet.cell_value(row,11),         #10 3
            'interest_fan':sheet.cell_value(row,12)             #11 3
        }

        # split_tags(data_dic['city'], 12, 4)
        #
        # split_tags(data_dic['profession_skill'], 5, 2)
        # split_tags(data_dic['profession_industry'], 6, 2)
        # split_tags(data_dic['profession_designation'], 7, 2)
        #
        # split_tags(data_dic['legacy_work'], 1, 1)
        # split_tags(data_dic['legacy_education'], 2, 1)
        # split_tags(data_dic['legacy_hometown'], 3, 1)
        # split_tags(data_dic['legacy_lifestyle'], 4, 1)
        #
        # split_tags(data_dic['interest_cause'], 8, 3)
        # split_tags(data_dic['interest_hobby'], 9, 3)
        # split_tags(data_dic['interest_sports'], 10, 3)
        # split_tags(data_dic['interest_fan'], 11, 3)
        #
        # split_tags("legacy_any", 16, 5)
        # split_tags("profession_any", 16, 5)
        # split_tags("interest_any", 16, 5)
        # split_tags("Global", 16, 5)


        all_data.append(data_dic)

    return all_data

def split_tags(tags,attribute_id,category_id):

    '''function to split the tags'''

    if tags == '':
        return
    tags=tags.split(",")
    tag_list=[]

    for tag in tags:
        tag=tag.strip()
        tag_id=create_or_get_tag(tag,attribute_id,category_id)
        tag_list.append(tag_id)

    return tag_list



def create_or_get_tag(tag_name,attribute_id,category_id):

    '''function to get the id of the tag and if tag is already not present create a new one and send id'''

    id=is_tag_present(tag_name,attribute_id,category_id)

    if id:
        return id

    try:
        conn=get_connection()
        curr=conn.cursor()
        sql="insert into togther_tags_lpig(name,attribute_id_id,category_id_id) values(%s,%s,%s)"
        parameter=[tag_name,attribute_id,category_id]
        curr.execute(sql,parameter)
        conn.commit()
        count = curr.rowcount
        print(count, "Record inserted successfully into tags_lpig table")
        curr.close()
        conn.close()
        id=is_tag_present(tag_name,attribute_id,category_id)
        if id:
            return id
    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting  to PostgreSQL", error)


def get_user_id(email):

    '''function to get user if from mail'''

    email=email.strip().lower()
    try:
        conn = get_connection()
        curr = conn.cursor()
        sql="select user_id_id from togther_userinfo where email=%s"
        parameter=[email]
        curr.execute(sql,parameter)
        res = curr.fetchone()
        curr.close()
        conn.close()
        if res:
            return res[0]
        else:
            return False

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)


def is_tag_present(tag_name,attribute_id,category_id):

    '''function to check if the tag is already present or not'''


    try:
        conn=get_connection()
        curr=conn.cursor()
        sql="select id from togther_tags_lpig where name=%s and attribute_id_id=%s and category_id_id=%s"
        parameter=[tag_name,attribute_id,category_id]
        curr.execute(sql,parameter)
        res=curr.fetchone()
        curr.close()
        conn.close()
        if res:
            return res[0]
        return False
    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting  to PostgreSQL", error)



def get_all_list(data_dic):

    '''function to get all list of users'''

    legacy_list = []

    legacy = split_tags(data_dic['legacy_work'], 1, 1)
    if legacy is not None:
        legacy_list.append(legacy)

    legacy = split_tags(data_dic['legacy_education'], 2, 1)
    if legacy is not None:
        legacy_list.append(legacy)

    legacy = split_tags(data_dic['legacy_hometown'], 3, 1)
    if legacy is not None:
        legacy_list.append(legacy)

    legacy = split_tags(data_dic['legacy_lifestyle'], 4, 1)
    if legacy is not None:
        legacy_list.append(legacy)
    legacy = split_tags("legacy_any", 16, 5)
    legacy_list.append(legacy)
    global_legacy = []

    for legacy in legacy_list:
        for data in legacy:
            global_legacy.append(data)

    # filling the profession list

    profession_list = []

    profession = split_tags(data_dic['profession_skill'], 5, 2)

    if profession is not None:
        profession_list.append(profession)

    profession = split_tags(data_dic['profession_industry'], 6, 2)
    if profession is not None:
        profession_list.append(profession)

    profession = split_tags(data_dic['profession_designation'], 7, 2)
    if profession is not None:
        profession_list.append(profession)

    profession = split_tags("profession_any", 16, 5)
    profession_list.append(profession)

    global_profession = []
    for profession in profession_list:
        for data in profession:
            global_profession.append(data)

    # filling the interest list

    interest_list = []

    interest = split_tags(data_dic['interest_cause'], 8, 3)
    if interest is not None:
        interest_list.append(interest)

    interest = split_tags(data_dic['interest_hobby'], 9, 3)
    if interest is not None:
        interest_list.append(interest)

    interest = split_tags(data_dic['interest_sports'], 10, 3)
    if interest is not None:
        interest_list.append(interest)

    interest = split_tags(data_dic['interest_fan'], 11, 3)
    if interest is not None:
        interest_list.append(interest)

    interest = split_tags("interest_any", 16, 5)
    interest_list.append(interest)
    global_interest = []

    for interest in interest_list:
        for data in interest:
            global_interest.append(data)

    # geography list
    geo_list = []
    geo = split_tags(data_dic['city'], 12, 4)
    geo_list.append(geo)

    geo = split_tags("Global", 16, 5)
    geo_list.append(geo)
    global_geo = []

    for geo in geo_list:
        for data in geo:
            global_geo.append(data)

    return (global_legacy,global_profession,global_interest,global_geo)



def fill_user_tags(user_id,all_tags):

    '''function to insert user tags '''

    legacy=json.dumps(all_tags[0])
    profession = json.dumps(all_tags[1])

    interests = json.dumps(all_tags[2])

    geography = json.dumps(all_tags[3])

    try:
            conn=get_connection()
            curr=conn.cursor()
            sql="insert into togther_user_lpig(member_id_id,legacy,profession,interests,geography) values(%s,%s,%s,%s,%s)"
            parameters=[user_id,legacy,profession,interests,geography]
            curr.execute(sql,parameters)
            conn.commit()
            count = curr.rowcount
            print(count, "Record inserted successfully into tags_lpig table")
            curr.close()
            conn.close()

    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting  to PostgreSQL", error)


if __name__=="__main__":

    # read_excell_file(True)

   current_time=time.time()
   all_data=read_excell_file()

   for data_dic in all_data:

       user_id=get_user_id(data_dic['email'])

       if user_id:
            all_tags=get_all_list(data_dic)
            fill_user_tags(user_id,all_tags)


   print("Executing time:")
   print(time.time()-current_time)
      
      
      



      
          
          
    


     

























