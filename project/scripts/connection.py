
# file to make database connection and return a connection object

import  psycopg2

# production
# db_user="nateshr"
# db_password="connectNRpostgresql"
# db_host= 'collabmatesdatabase.cgx3gr7xnezq.ap-south-1.rds.amazonaws.com'
# db_database="togther"
# db_port="5432"


#development

db_user="postgres"
db_password="postgres"
db_host= '13.235.187.102'
db_database="production_dump"
db_port="5432"


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

