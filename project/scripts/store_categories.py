import  psycopg2
from connection import  get_connection

def insert_categories(name):

    '''function to insert categories'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        sql="insert into togther_category(name) values(%s)"
        parameter=[name]
        curr.execute(sql,parameter)
        conn.commit()
        count = curr.rowcount
        print(count, "Record inserted successfully into mobile table")
        curr.close()
        conn.close()
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)



def insert_attributes(name,category_id):

    '''function to insert categories'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        sql="insert into togther_attributes(attribute_name,category_id_id) values(%s,%s)"
        parameter=[name,category_id]
        curr.execute(sql,parameter)
        conn.commit()
        count = curr.rowcount
        print(count, "Record inserted successfully into  table")
        curr.close()
        conn.close()
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)


if __name__=="__main__":

    #inserting category in tags
    insert_categories("Legacy")
    insert_categories("Profession")
    insert_categories("Interests")
    insert_categories("Geography")
    insert_categories("Global")


    #inserting attribues
    insert_attributes("Legacy_work",1)
    insert_attributes("Legacy_education",1)
    insert_attributes("Legacy_hometown",1)
    insert_attributes("Legacy_lifestyle",1)

    insert_attributes("Profession_skill",2)
    insert_attributes("Profession_industry",2)
    insert_attributes("Profession_designation",2)

    insert_attributes("Interests_cause",3)
    insert_attributes("Interests_hobby",3)
    insert_attributes("Interests_sports",3)
    insert_attributes("Interests_fan",3)

    insert_attributes("Geography_city",4)
    insert_attributes("Geography_state", 4)
    insert_attributes("Geography_country", 4)
    insert_attributes("Geography_pincode", 4)

    insert_attributes("Global",5)











