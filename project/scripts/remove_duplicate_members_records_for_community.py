from togther.models import (Members, ModelUtilities)
import psycopg2
from django.conf import settings
from collabmates_api.notification import (get_connection)


if settings.IS_BETA:
    community_id = None

else:
    community_id = 0


def get_duplicate_user_community_ids_map():
    try:
        conn = get_connection()
        curr = conn.cursor()

        community_id_query = ""

        if community_id is not None:
            community_id_query = "WHERE community_id_id={}".format(community_id)

        sql = """
                WITH added_row_number
                     AS (SELECT id,
                                member_id_id,
                                community_id_id,
                                Row_number()
                                  OVER(
                                    partition BY community_id_id, member_id_id
                                    ORDER BY updated_at DESC)
                         FROM   togther_members AS mems {})
                SELECT id,
                       member_id_id,
                       community_id_id,
                       row_number
                FROM   added_row_number
                WHERE  row_number > 1;
        """.format(community_id_query)

        curr.execute(sql)
        res = curr.fetchall()
        curr.close()

        return res

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL %s ", error)


def remove_duplicate_members_table_records():
    duplicate_member_ids_data = get_duplicate_user_community_ids_map()

    member_ids = [members_tuple[0] for members_tuple in duplicate_member_ids_data]

    if member_ids:
        ModelUtilities.delete_record_in_model(Members, {'id__in': member_ids})

    print("Deleted {} records!".format(len(member_ids)))
