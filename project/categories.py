import psycopg2
from django.conf import  settings

# file to store configuration of the system


# database details
db_user="apoorv"
db_password="khare"
db_host=settings.DB_HOST
db_database="togther"



Category_list_backup = [
{ "id" : 'al' , "title": 'Alumni'},
{ "id" : 'cl' , "title": 'College'},
{ "id" : 'sc' , "title": 'School'},
{ "id" : 'pf' , "title": 'Profession'},
{ "id" : 'nr' , "title": 'Native Roots'},
{ "id" : 'pa' , "title": 'Parenting'},
{ "id" : 'ev' , "title": 'Events'},
{ "id" : 'in' , "title":  'Interests'},
{ "id" : 'ed' , "title": 'Education'},
{ "id" : 'ac' , "title": 'Achievements'},
{ "id" : 'le' , "title": 'Learning'},
{ "id" : 'op' , "title": 'Opportunities'},
{ "id" : 'sp' , "title": 'Sports'},
{ "id" : 'ac' , "title": 'Activities'},
{ "id" : 'tr' , "title": 'Travel'},
{ "id" : 'ho' , "title": 'Hobbies'},
{ "id" : 're' , "title": 'Religious'},
{ "id" : 'po' , "title": 'Political'},
{ "id" : 'so' , "title": 'Social'},
{ "id" : 'mu' , "title": 'Music'},
{ "id" : 'be' , "title": 'Belief'},
{ "id" : 'fa' , "title": 'Fan'},
{ "id" : 'st' , "title": 'Startups'},
{ "id" : 'fi' , "title": 'Finance'},
{ "id" : 'in' , "title": 'Industry'},
{ "id" : 'sk' , "title": 'Skill'},
{ "id" : 'fa' , "title": 'Family'},
{ "id" : 'ca' , "title": 'Cause'},
{ "id" : 'ne' , "title": 'Neighborhood'},
{ "id" : 'hw' , "title": 'Health & Wellness'},
{ "id" : 'sf' , "title": 'Sports & Fitness'},
{ "id" : 'fd' , "title": 'Food & Drink'},
{ "id" : 'lc' , "title": 'Language & Culture'},
{ "id" : 'mo' , "title": 'Movement'},
{ "id" : 'ga' , "title": 'Games'},
{ "id" : 'ar' , "title": 'Art'},
{ "id" : 'fa' , "title": 'Fashion'},
{ "id" : 'br' , "title": 'Brand'},
{ "id" : 'le' , "title": 'Learning'},
{ "id" : 'lg' , "title": 'Legacy'},

]

Category_list = [
{ "id" : 'in' , "title":  'Interests'},
{ "id" : 'ca' , "title": 'Cause'},
{ "id" : 'ind', "title": 'Industry'},
{ "id" : 'pf' , "title": 'Profession'},
{ "id" : 'fa' , "title": 'Fan'},
{ "id" : 'sf' , "title": 'Sports'},
{ "id" : 'lg' , "title": 'Legacy'},
{ "id" : 'le' , "title": 'Learning'},
]

def get_connection():
    '''function to create a postgres connection'''
    try:
        connection = psycopg2.connect(user=db_user,
                                      password=db_password,
                                      host=db_host,
                                      port=db_port,
                                      database=db_database)
        return connection
    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting  to PostgreSQL", error)


def add_cateogy_to_database(categoty_id,category_name):

    try:
        connection=get_connection()
        curr=connection.cursor()
        sql="insert into togther_tags(category_id,category_name) values(%s,%s)"
        parameter_list=[categoty_id,category_name]
        curr.execute(sql,parameter_list)
        connection.commit()
        curr.close()
        connection.close()
    except (Exception, psycopg2.Error) as error:
        print ("Error while connecting to PostgreSQL", error)


def run():

    for category in Category_list_backup:
        add_cateogy_to_database(category['id'],category['title'])
    print('Inserted Successfully')







