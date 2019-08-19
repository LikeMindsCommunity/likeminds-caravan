
# file to make database connection and return a connection object

import  psycopg2

db_user="apoorv"
db_password="khare"
db_host="13.235.187.102"
db_database="togther"
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


