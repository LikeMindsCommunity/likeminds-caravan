from __future__ import absolute_import, unicode_literals
import psycopg2

from utility.time_utilities import TimeUtilities

from .constants import RESOURCE_TYPE
from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()

envir = False

try:
    from collabmates_api.notification import get_connection
    from project.celery import app

except:
    envir = True
    import sys

    sys.path.append("..")
    from scripts.connection import get_connection
    from project.celery import app


def fetch_child_url_ids_for_updating_permission(category_id, cohort_id, access_type_list):
    try:
        conn = get_connection()
        curr = conn.cursor()

        if len(access_type_list) == 1:
            access_type_query = "AND access_type = %s" % str(access_type_list[0])

        else:
            access_type_query = "AND access_type in %s" % str(tuple(access_type_list))

        sql = """
                SELECT      DISTINCT(trup.url_id_id)
                FROM        togther_resource_url_parent_category trupc
                INNER JOIN  togther_resource_url_permission trup
                ON          trupc.url_id_id = trup.url_id_id 
                WHERE       trupc.category_id_id='%s'
                AND         cohort_id_id=%s
                    %s
            """ % (str(category_id), str(cohort_id), access_type_query)

        curr.execute(sql)
        child_urls = curr.fetchall()
        curr.close()

        return child_urls

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def fetch_child_file_ids_for_updating_permission(category_id, cohort_id, access_type_list):
    try:
        conn = get_connection()
        curr = conn.cursor()

        if len(access_type_list) == 1:
            access_type_query = "AND access_type = %s" % str(access_type_list[0])

        else:
            access_type_query = "AND access_type in %s" % str(tuple(access_type_list))

        sql = """
                SELECT      DISTINCT(trfp.file_id_id)
                FROM        togther_resource_file_parent_category trfpc
                INNER JOIN  togther_resource_file_permission trfp
                ON          trfpc.file_id_id = trfp.file_id_id 
                WHERE       trfpc.category_id_id='%s'
                AND         cohort_id_id=%s
                    %s 
            """ % (str(category_id), str(cohort_id), access_type_query)

        curr.execute(sql)
        child_files = curr.fetchall()
        curr.close()

        return child_files

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def fetch_child_category_ids_for_updating_permission(category_id, cohort_id, access_type_list):
    try:
        conn = get_connection()
        curr = conn.cursor()

        if len(access_type_list) == 1:
            access_type_query = "AND access_type = %s" % str(access_type_list[0])

        else:
            access_type_query = "AND access_type in %s" % str(tuple(access_type_list))

        sql = """
                SELECT      DISTINCT(trcp.category_id_id)
                FROM        togther_resource_category_parent_category trcpc
                INNER JOIN  togther_resource_category_permission trcp
                ON          trcpc.child_category_id_id = trcp.category_id_id 
                WHERE       trcpc.category_id_id='%s'
                AND         cohort_id_id=%s
                    %s 
            """ % (str(category_id), str(cohort_id), access_type_query)

        curr.execute(sql)
        child_categorys = curr.fetchall()
        curr.close()

        return child_categorys

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_parent_categories_with_access_type(resource_type, resource_id, cohort_id, access_type_list):
    try:
        conn = get_connection()
        curr = conn.cursor()

        if len(access_type_list) == 1:
            access_type_query = "AND access_type = %s" % str(access_type_list[0])

        else:
            access_type_query = "AND access_type in %s" % str(tuple(access_type_list))

        if resource_type == RESOURCE_TYPE.URL:
            parent_mapping_schema = "togther_resource_url_parent_category"
            filter_clause = "child.url_id_id='%s'" % resource_id

        elif resource_type == RESOURCE_TYPE.FILE:
            parent_mapping_schema = "togther_resource_file_parent_category"
            filter_clause = "child.file_id_id='%s'" % resource_id

        elif resource_type == RESOURCE_TYPE.CATEGORY:
            parent_mapping_schema = "togther_resource_category_parent_category"
            filter_clause = "child.child_category_id_id='%s'" % resource_id

        sql = """
                SELECT      DISTINCT(child.category_id_id)
                FROM        %s child
                INNER JOIN  togther_resource_category_permission trcp
                ON          child.category_id_id = trcp.category_id_id
                WHERE       %s
                AND         cohort_id_id=%s
                    %s
            """ % (
                parent_mapping_schema,
                filter_clause,
                str(cohort_id),
                access_type_query
            )

        curr.execute(sql)
        parent_categories = curr.fetchall()
        curr.close()

        return parent_categories

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)

def get_child_resource_state_for_category(resource_type, state, member_id, child_categories):
    try:
        conn = get_connection()
        curr = conn.cursor()

        if len(child_categories) == 1:
            child_category_query = "WHERE category_id_id = '%s'" % str(child_categories[0])

        else:
            child_category_query = "WHERE category_id_id in %s" % str(tuple(child_categories))

        if resource_type == RESOURCE_TYPE.URL:
            resource_id = "url_id_id"
            state_schema = "togther_resource_url_state"
            parent_mapping_schema = "togther_resource_url_parent_category"

        elif resource_type == RESOURCE_TYPE.FILE:
            resource_id = "file_id_id"
            state_schema = "togther_resource_file_state"
            parent_mapping_schema = "togther_resource_file_parent_category"

        sql = """
                SELECT  DISTINCT(%s)
                FROM    %s
                WHERE   user_id_id=%s
                AND     state=%s
                AND     %s in (
                            SELECT  %s
                            FROM    %s
                            %s
                        )
            """ % (
                resource_id,
                state_schema,
                str(member_id),
                str(state),
                resource_id,
                resource_id,
                parent_mapping_schema,
                child_category_query
            )

        curr.execute(sql)
        query = curr.fetchall()
        curr.close()

        child_ids = [data[0] for data in query]

        return child_ids

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)
