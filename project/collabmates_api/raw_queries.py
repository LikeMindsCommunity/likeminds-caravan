from __future__ import absolute_import, unicode_literals
from celery import shared_task
import time
import logging
import psycopg2
from utility.states import (card_types, conversation_states, SyncTypes, noti_states)
from utility.utils import is_version_code_supported_for_intro_room
from .static_text import (MIN_NUMBER_OF_PIN_CHATROOMS_IN_FEED_REVAMP, SPECIFIC_MEMBER_TAG_REGEX, EVERYONE_TAG_REGEX,
                          PARTICIPANTS_TAG_REGEX)
from collabmates_api.static_files import (REMOVED_USER_URL)

from external_services.logging.logging_wrapper import LoggingWrapper

from utility.time_utilities import TimeUtilities

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()

envir = False

try:
    from .notification import get_connection
    from project.celery import app

except:
    envir = True
    import sys

    sys.path.append("..")
    from scripts.connection import get_connection
    from project.celery import app


def update_conversation_engage_for_chatrooms(card_id, user_id, last_conversation_id, unseen_count):
    '''function to update chatroom data'''

    try:
        current_time = TimeUtilities.current_time_in_milliseconds()

        error_logger.error(f"[raw_query] starting update_conversation_engage_for_chatrooms - {card_id} {user_id} {last_conversation_id} {unseen_count}")
        conn = get_connection()
        curr = conn.cursor()

        sql = """update togther_conversationengage set last_conversation_id = %s ,unseen_count = %s where card_id=%s and user_id = %s"""
        paramter_list = [last_conversation_id, unseen_count, card_id, user_id]
        curr.execute(sql, paramter_list)
        conn.commit()
        info_logger.info("conversation engage updated successfully")
        curr.close()

        end_time = TimeUtilities.current_time_in_milliseconds()

        error_logger.error(f"[raw_query] ({current_time - end_time} ms) done update_conversation_engage_for_chatrooms - {card_id} {user_id} {last_conversation_id} {unseen_count}")

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


@shared_task
def update_conversation_engage_data_for_chatroom(card_id, user_id, updated_at):
    '''function to update chatroom data'''

    try:
        
        current_time = TimeUtilities.current_time_in_milliseconds()

        error_logger.error(f"[raw_query] starting update_conversation_engage_data_for_chatroom - {card_id} {user_id} {updated_at}")

        conn = get_connection()
        curr = conn.cursor()

        sql = """
                UPDATE togther_conversationengage
                SET    unseen_count = (
                       CASE
                              WHEN user_id!=%s THEN unseen_count + 1
                              ELSE 0
                       END),
                       updated_at=%s
                WHERE  card_id=%s;"""
        paramter_list = [user_id, updated_at, card_id]
        curr.execute(sql, paramter_list)
        conn.commit()
        info_logger.info("conversation engage updated successfully")
        curr.close()

        end_time = TimeUtilities.current_time_in_milliseconds()
        error_logger.error(f"[raw_query] ({current_time - end_time} ms) done update_conversation_engage_data_for_chatroom - {card_id} {user_id} {updated_at}")

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_my_chatrooms_count(user_id,
                           version_code,
                           platform_code,
                           chatroom_type,
                           consider_dm_chatrooms=False,
                           dm_instance_community_ids_list=[],
                           community_id=None,
                           intro_room_community_list=[],
                           should_add_dm_chatrooms=False,
                           custom_tag=""):
    '''function to give the count of active my chatrooms'''
    try:
        is_private = "FALSE"
        chatroom_with_user_id_val = "NULL"
        dm_chatrooms_communities_filter = ""

        if community_id:
            dm_chatrooms_communities_filter = f"AND togther_collabcard.community_id IN ({str(community_id)})"

        if consider_dm_chatrooms and len(dm_instance_community_ids_list) == 0:
            return 0

        if consider_dm_chatrooms and len(dm_instance_community_ids_list) != 0:
            is_private = "TRUE"
            chatroom_with_user_id_val = "NOT NULL"
            dm_chatrooms_communities_filter = "AND togther_collabcard.community_id IN (%s)" % ",".join([
                str(i) for i in dm_instance_community_ids_list])

        if is_version_code_supported_for_intro_room(version_code, platform_code):

            if intro_room_community_list:
                intro_filter_list_str = ",".join([str(i) for i in intro_room_community_list])
                filter_intro_rooms_query = """
                CASE WHEN togther_collabcard.community_id IN ( %s ) THEN togther_collabcard.user_id != %s
                                                AND togther_collabcard.type = 1
                ELSE togther_collabcard.type IN ( 1, 9 ) END
                """ % (intro_filter_list_str, user_id)

            else:
                filter_intro_rooms_query = """togther_collabcard.type IN ( 1, 9 )"""

        else:
            filter_intro_rooms_query = """togther_collabcard.type = -1"""

        excluded_card_ids_filter = """"""

        dm_chatrooms_filter = """togther_collabcard.is_private = {} 
                                 AND togther_collabcard.is_private_member = FALSE 
                                 AND togther_collabcard.chatroom_with_user_id IS {} AND""".format(
            is_private, chatroom_with_user_id_val)

        if should_add_dm_chatrooms:
            dm_chatrooms_filter = ""

        chatroom_type_filter = """"""
        if chatroom_type != -1:
            chatroom_type_filter = """ AND togther_collabcard.type in (%s)""" % str(chatroom_type)

        custom_tag_filter = ""
        if custom_tag:
            custom_tag_filter = f""" AND togther_collabcard.custom_tag ILIKE '%{custom_tag.replace("'", "''")}%'"""

        conn = get_connection()
        curr = conn.cursor()

        sql = """
                SELECT COUNT(card_id)
                FROM   togther_collabcardstate
                INNER JOIN togther_collabcard
                ON togther_collabcardstate.card_id = togther_collabcard.id
                WHERE  togther_collabcardstate.user_id = %s
                    AND togther_collabcardstate.follow_status = TRUE
                    AND ( togther_collabcardstate.remove_id IS NULL )
                    AND togther_collabcardstate.secret_chatroom_left = FALSE
                    AND (%s togther_collabcard.is_deleted = FALSE
                    AND not (%s) %s) %s %s %s""" % (
            str(user_id),
            dm_chatrooms_filter,
            str(filter_intro_rooms_query),
            dm_chatrooms_communities_filter,
            excluded_card_ids_filter,
            chatroom_type_filter,
            custom_tag_filter
        )

        curr.execute(sql)
        count = curr.fetchone()
        curr.close()

        return count[0]

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_card_ids_to_exclude_based_on_cohort_access(user_id, community_id=None):
    community_based_filter = """"""

    if community_id:
        community_based_filter = """AND chatroom_id IN (SELECT id
                                           FROM   togther_collabcard
                                           WHERE  community_id = %s)""" % (str(community_id))
    try:

        conn = get_connection()
        curr = conn.cursor()

        sql = """
                SELECT chatroom_id
                FROM   togther_ChatroomCohort
                WHERE  cohort_id IN (SELECT cohort_id
                                     FROM   togther_CohortMember
                                     WHERE  user_id = %s) %s
                GROUP  BY chatroom_id
                HAVING MAX(cohort_access) = 0;
            """ % (str(user_id), community_based_filter)

        curr.execute(sql)
        res = curr.fetchall()

        card_ids = []
        for card_id in res:
            card_ids.append(card_id[0])

        curr.close()

        return card_ids

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_chatrooms_of_user_with_follow_status(user_id, community_id: str = None, follow_status: str = True):
    community_based_filter = ""

    if community_id:
        community_based_filter = """AND togther_collabcardState.community_id = %s""" % (str(community_id))

    try:

        conn = get_connection()
        curr = conn.cursor()

        sql = """
                SELECT togther_collabcard.id
                FROM togther_collabcard
                INNER JOIN togther_collabcardState
                    ON togther_collabcardState.card_id = togther_collabcard.id
                WHERE togther_collabcardState.user_id=%s
                        AND follow_status = %s
                        AND togther_collabcardState.remove_id is NULL %s;
            """ % (str(user_id), follow_status, community_based_filter)

        curr.execute(sql)
        res = curr.fetchall()

        card_ids = []
        for card_id in res:
            card_ids.append(card_id[0])

        curr.close()

        return card_ids

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_followed_chatrooms(user_id,
                           page,
                           version_code,
                           platform_code,
                           chatroom_type,
                           limit=10,
                           consider_dm_chatrooms=False,
                           dm_instance_community_ids_list=[],
                           community_id=None,
                           intro_room_community_list=[],
                           should_add_dm_chatrooms=False,
                           custom_tag=''):
    '''function to get the active followed chatroom count'''
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        is_private_val = "FALSE"
        chatroom_with_user_val = "NULL"
        dm_chatrooms_communities_filter = ""
        conversation_communities_filter = ""

        if community_id:
            dm_chatrooms_communities_filter = f"AND togther_collabcard.community_id IN ({str(community_id)})"
            conversation_communities_filter = f"WHERE community_id IN ({str(community_id)})"

        if consider_dm_chatrooms and len(dm_instance_community_ids_list) == 0:
            return []

        if consider_dm_chatrooms and len(dm_instance_community_ids_list) != 0:
            is_private_val = "TRUE"
            chatroom_with_user_val = "NOT NULL"
            dm_chatrooms_communities_filter = "AND togther_collabcard.community_id IN (%s)" % ",".join([
                str(i) for i in dm_instance_community_ids_list])

        if is_version_code_supported_for_intro_room(version_code, platform_code):

            if intro_room_community_list:
                intro_filter_list_str = ",".join([str(i) for i in intro_room_community_list])
                filter_intro_rooms_query = """
                CASE WHEN togther_collabcard.community_id IN ( %s ) THEN togther_collabcard.user_id != %s
                                                AND togther_collabcard.type = 1
                ELSE togther_collabcard.type IN ( 1, 9 ) END
                """ % (intro_filter_list_str, user_id)

            else:
                filter_intro_rooms_query = """togther_collabcard.type IN ( 1, 9 )"""

        else:
            filter_intro_rooms_query = """togther_collabcard.type = -1"""

        excluded_card_ids_filter = ""

        dm_chatrooms_filter = """togther_collabcard.is_private = {}
                                 AND togther_collabcard.is_private_member = FALSE
                                 AND togther_collabcard.chatroom_with_user_id IS {} AND""".format(
            is_private_val, chatroom_with_user_val)

        if should_add_dm_chatrooms:
            dm_chatrooms_filter = ""

        included_conversation_states = get_tuple_from_array([
            conversation_states.ANSWER, conversation_states.CONVERSATION_POLL, conversation_states.CONVERSATION_EVENT,
            conversation_states.CONVERSATION_HEADER,
            conversation_states.CONVERSATION_DIRECT_MESSAGE_BLOCK_MEMBER_DISABLE_CHAT,
            conversation_states.CONVERSATION_DIRECT_MESSAGE_UNBLOCK_MEMBER_ENABLE_CHAT
        ])

        follow_conversation_state = get_tuple_from_array([conversation_states.CONVERSATION_FOLLOW])

        chatroom_type_filter = """ AND togther_collabcard.type not in (%s)""" % str(card_types.CARD_FEED_GROUP)
        if chatroom_type != -1:
            chatroom_type_filter = """ AND togther_collabcard.type in (%s)""" % str(chatroom_type)

        custom_tag_filter = ""
        if custom_tag:
            custom_tag_filter = f""" AND togther_collabcard.custom_tag ILIKE '%{custom_tag.replace("'", "''")}%'"""

        conn = get_connection()
        curr = conn.cursor()

        # fetch_card_ids_sql = """SELECT card_id
        #                         FROM   togther_collabcardstate
        #                         WHERE  user_id = %s
        #                         AND    follow_status = true
        #                         AND    (
        #                                       remove_id IS NULL)
        #                         AND    secret_chatroom_left=false
        #                         AND    card_id IN
        #                                (
        #                                       SELECT id
        #                                       FROM   togther_collabcard
        #                                       WHERE  (%s    is_deleted = FALSE
        #                                              AND    NOT (%s)
        #                                             %s) %s %s %s)""" % (
        #     str(user_id),
        #     str(dm_chatrooms_filter),
        #     str(filter_intro_rooms_query),
        #     str(dm_chatrooms_communities_filter),
        #     str(excluded_card_ids_filter),
        #     str(chatroom_type_filter),
        #     custom_tag_filter)
        #
        # curr.execute(fetch_card_ids_sql)
        # card_ids_res = curr.fetchall()

        card_ids_list = []

        # for id in card_ids_res:
        #     card_ids_list.append(id[0])

        card_ids = get_tuple_from_array(card_ids_list)

        sql = """
                SELECT     togther_collabcardstate.card_id,
                           lca.created_at
                FROM       togther_collabcardstate
                INNER JOIN (WITH added_row_number AS
                           (
                                    SELECT   ca.created_at,
                                             ca.id,
                                             ca.card_id,
                                             row_number() OVER( partition BY ca.card_id ORDER BY (
                                             CASE
                                                      WHEN ca.state IN %s
                                                      OR       (
                                                                        ca.state IN %s
                                                               AND      ca.user_id = %s) THEN 1
                                                      ELSE 2
                                             END), ca.created_at DESC) AS row_number,
                                             CASE
                                                      WHEN ca.state IN %s
                                                      OR       (
                                                                        ca.state IN %s
                                                               AND      ca.user_id = %s) THEN 1
                                                      ELSE 2
                                             END                  AS cond_row
                                    FROM     togther_card_answers AS ca %s
                                    ) SELECT   card_id,
                           id,
                           created_at,
                           cond_row
                  FROM     added_row_number
                  WHERE    row_number = 1) AS lca
                  ON       togther_collabcardstate.card_id = lca.card_id
                  INNER JOIN togther_collabcard
                  ON togther_collabcard.id = togther_collabcardstate.card_id
                  WHERE  togther_collabcardstate.user_id = %s
                                AND    togther_collabcardstate.follow_status = true
                                AND    (
                                              togther_collabcardstate.remove_id IS NULL)
                                AND    togther_collabcardstate.secret_chatroom_left=false
                                AND    (%s    togther_collabcard.is_deleted = FALSE
                                                     AND    NOT (%s)
                                                    %s) %s %s %s
                  ORDER BY lca.cond_row,
                           lca.created_at DESC,
                           lca.id DESC limit %s offset %s""" % (
            included_conversation_states, follow_conversation_state, user_id, included_conversation_states,
            follow_conversation_state, user_id, conversation_communities_filter, str(user_id),
            str(dm_chatrooms_filter), str(filter_intro_rooms_query), str(dm_chatrooms_communities_filter),
            str(excluded_card_ids_filter), str(chatroom_type_filter), custom_tag_filter, str(limit), str(offset))

        curr.execute(sql)
        res = curr.fetchall()

        engage_list = {id[0]: id[1] for id in res}

        curr.close()

        return engage_list

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  %s", error)


def get_draft_chatrooms_on_home_screen(user_id, page, community_id):
    '''api to get draft chatroom home-screen'''

    try:
        page_number = int(page)
        limit = 10
        offset = (page_number - 1) * 10

        community_filter = ""
        if community_id:
            community_filter = f"AND community_id = {str(community_id)}"

        conn = get_connection()
        curr = conn.cursor()
        sql = """SELECT id,
                        card_id,
                        draft_id
                FROM togther_conversationEngage
                WHERE user_id =%s
                %s
                ORDER BY updated_at desc, id DESC 
                limit %s 
                offset %s""" % (
            str(user_id),
            community_filter,
            str(limit),
            str(offset))

        curr.execute(sql)
        res = curr.fetchall()

        draft_list = []

        for data in res:
            if data[2]:
                draft_list.append(data[0])
        curr.close()

        return draft_list

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


@shared_task
def update_community_purpose_card(community_id, card_id):
    '''function to update community pupose collabcard'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        info_logger.info(card_id)
        info_logger.info(community_id)
        sql = """update togther_community set purpose_collabcard=%s where id=%s""" % (card_id, community_id)
        info_logger.info(sql)
        curr.execute(sql)
        conn.commit()
        info_logger.info("purpose updated successfully")
        curr.close()

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_all_data(sql):
    '''function to get all data based on a sql query'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        curr.execute(sql)
        res = curr.fetchall()
        curr.close()

        if res:
            return res
        return []

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def filter_tags(user_id=0, community_id=0):
    '''function to return the filtered tags based on LPIG'''
    legacy = []
    profession = []
    interest = []
    geo_list = []
    sql = ""

    if community_id:
        sql = "select correct_tag_id from togther_community_legacy where community_id_id=" + str(community_id)
        tags = get_all_data(sql)

        legacy = []
        for data in tags:
            legacy.append(data[0])
        # legacy=get_list_of_tag_id(legacy,hashmap)

        sql = "select correct_tag_id from togther_community_profession where community_id_id=" + str(community_id)
        tags = get_all_data(sql)
        profession = []
        for data in tags:
            profession.append(data[0])
        # profession=get_list_of_tag_id(profession,hashmap)

        sql = "select correct_tag_id from togther_community_interest where community_id_id=" + str(community_id)
        tags = get_all_data(sql)
        interest = []
        for data in tags:
            interest.append(data[0])
        # interest = get_list_of_tag_id(interest, hashmap)

        sql = "select correct_tag_id from togther_community_geography where community_id_id=" + str(community_id)
        tags = get_all_data(sql)
        geo_list = []
        for data in tags:
            geo_list.append(data[0])
        # geo_list = get_list_of_tag_id(geo_list, hashmap)

    if user_id:
        sql = "select correct_tag_id from togther_user_legacy where user_id_id=" + str(user_id)
        tags = get_all_data(sql)
        if not tags:
            return False
        legacy = []
        for data in tags:
            legacy.append(data[0])
        # legacy = get_list_of_tag_id(legacy, hashmap)

        sql = "select correct_tag_id from togther_user_profession where user_id_id=" + str(user_id)
        tags = get_all_data(sql)
        if not tags:
            return False
        profession = []
        for data in tags:
            profession.append(data[0])
        # profession = get_list_of_tag_id(profession, hashmap)

        sql = "select correct_tag_id from togther_user_interest where user_id_id=" + str(user_id)
        tags = get_all_data(sql)
        if not tags:
            return False
        interest = []
        for data in tags:
            interest.append(data[0])
        # interest = get_list_of_tag_id(interest, hashmap)

        sql = "select correct_tag_id from togther_user_geography where user_id_id=" + str(user_id)
        tags = get_all_data(sql)
        if not tags:
            return False
        geo_list = []
        for data in tags:
            geo_list.append(data[0])
        # geo_list = get_list_of_tag_id(geo_list, hashmap)

    tags = {}

    if user_id:
        tags['user_id'] = user_id

    if community_id:
        tags['community_id'] = community_id

    tags['legacy'] = legacy
    tags['profession'] = profession
    tags['interest'] = interest
    tags['geography'] = geo_list

    return tags


def get_relevant_score(user, community):
    '''function to get relevant score of community'''

    legacy_user_list = user['legacy']
    geo_user_list = user['geography']
    interest_user_list = user['interest']
    profession_user_list = user['profession']

    # community attributes
    legacy_community_list = community['legacy']
    geo_community_list = community['geography']
    interest_community_list = community['interest']
    profession_community_list = community['profession']

    count_legacy = 0
    count_geography = 0
    count_interest = 0
    count_profession = 0

    # for legacy in legacy_user_list:
    #     if legacy in legacy_community_list:
    #         count_legacy += 1

    if legacy_community_list is None or profession_community_list is None or interest_community_list is None:
        return (user['user_id'], community['community_id'], 0)

    for legacy in legacy_community_list:
        if legacy in legacy_user_list:
            count_legacy += 1

    if count_legacy != len(legacy_community_list):
        return (user['user_id'], community['community_id'], 0)

    for geography in geo_user_list:
        if geography in geo_community_list:
            count_geography += 1

    for interest in interest_user_list:
        if interest in interest_community_list:
            count_interest += 1

    for profession in profession_user_list:
        if profession in profession_community_list:
            count_profession += 1

    if count_legacy == 0 or count_geography == 0 or count_interest == 0 or count_profession == 0:
        relevance_score = 0
    elif count_legacy and count_geography and count_profession and count_interest:
        relevance_score = count_legacy + count_profession + count_interest + count_geography
    else:
        relevance_score = 0

    return (user['user_id'], community['community_id'], relevance_score)


# community ranking based on user tags

def ranking_tags(tag):
    '''function to map communities and user based on rank.It inserts data for the tags'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "insert into togther_community_rank(member_id_id,community_id_id,weight) values(%s,%s,%s)"
        parameter = [tag[0], tag[1], tag[2]]
        curr.execute(sql, parameter)
        conn.commit()
        count = curr.rowcount
        info_logger.info(count, "Record inserted successfully into community_rank table")
        curr.close()

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting  to PostgreSQL %s", error)


def delete_previous_data_for_user(user_id):
    '''function to delete tag by id'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "delete from togther_community_rank where member_id_id=%s"
        parameter = [user_id]
        curr.execute(sql, parameter)
        conn.commit()
        curr.close()
        info_logger.info("Record deleted successfully for user:,", user_id)
    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting  to PostgreSQL %s", error)


def action_for_user_crete_or_community_create(user_id, community_id):
    '''function to handle the create user or create community'''

    user_tags = []
    community_tags = []
    if user_id is not None and community_id is None:
        all_user = [(user_id,)]
        delete_previous_data_for_user(user_id)  # deleting the previous data of user
        user_tags = []
        for user in all_user:
            filter_tag = filter_tags(user_id=user[0])
            user_tags.append(filter_tag)
        flag = False

        if user_tags and not flag:
            sql = """SELECT community_id_id
                            FROM togther_community_legacy
                            INNER JOIN togther_user_legacy
                            ON togther_community_legacy.correct_tag_id = togther_user_legacy.correct_tag_id
                            and togther_user_legacy.user_id_id=%s and community_id_id
                            in
                            (SELECT community_id_id
                            FROM togther_community_profession
                            INNER JOIN togther_user_profession
                            ON togther_community_profession.correct_tag_id = togther_user_profession.correct_tag_id
                            and togther_user_profession.user_id_id=%s and community_id_id
                            in
                            (SELECT community_id_id
                            FROM togther_community_interest
                            INNER JOIN togther_user_interest
                            ON togther_user_interest.correct_tag_id = togther_community_interest.correct_tag_id
                            and togther_user_interest.user_id_id=%s and community_id_id
                            in 
                            (SELECT community_id_id
                            FROM togther_community_geography
                            INNER JOIN togther_user_geography
                            ON togther_community_geography.correct_tag_id = togther_user_geography.correct_tag_id
                            and togther_user_geography.user_id_id=%s)))
                    """ % (user_id, user_id, user_id, user_id)
            all_communities = []
            flag = True
            data = get_all_data(sql)
            for i in data:
                all_communities.append(i[0])

        else:
            sql = "select distinct(community_id_id) from togther_community_legacy"
            all_communities = get_all_data(sql)

        community_tags = []

        for community in all_communities:
            if not flag:
                filter_tag = filter_tags(community_id=community[0])
            else:
                filter_tag = filter_tags(community_id=community)
            community_tags.append(filter_tag)

    elif user_id is None and community_id is not None:
        sql = "select distinct(user_id_id) from togther_user_legacy"
        all_user = get_all_data(sql)
        user_tags = []
        for user in all_user:
            filter_tag = filter_tags(user_id=user[0])
            user_tags.append(filter_tag)

        all_communities = [(community_id,)]
        community_tags = []
        for community in all_communities:
            filter_tag = filter_tags(community_id=community[0])
            community_tags.append(filter_tag)

    return (user_tags, community_tags)


@shared_task
def compute_rank(user_id=None, community_id=None):
    '''function to compute the rank of community '''
    info_logger.info("Executing Compute Rank for User", user_id)
    # clearing the custom_cache
    # custom_cache.clear()
    start_time = time.time()
    action = action_for_user_crete_or_community_create(user_id, community_id)
    user_tags = action[0]
    community_tags = action[1]
    for user in user_tags:
        for community in community_tags:
            score = get_relevant_score(user, community)
            if score[2] != 0:
                ranking_tags(score)

    end_time = time.time()

    info_logger.info("Compute rank execution time :", (end_time - start_time))


@app.task
def ranking_all_users_and_communities():
    '''function to rank all users and all communities to be triggered daily'''

    start_time = time.time()

    info_logger.info("Ranking All Users And Communities Based on tags")

    sql = "select user_id_id from togther_userinfo order by id desc"
    all_user = get_all_data(sql)
    for user in all_user:
        filter_tag = filter_tags(user_id=user[0])
        if filter_tag:
            compute_rank(user_id=user[0])
        else:
            info_logger.info("No Onboarding for user_id:", user[0])

    end_time = time.time()

    diff = (end_time - start_time)

    info_logger.info("Ranking Script Execution Time:", diff)


def get_chatroom_query_meta_for_sync():
    meta_query = """ togther_collabcard.id,
                    togther_collabcard.title,
                    togther_collabcard.community_id,
                    togther_collabcard.answer_text,
                    togther_collabcard.image_count,
                    togther_collabcard.pdf_count,
                    togther_collabcard.video_count,
                    togther_collabcard.audio_count,
                    togther_collabcard.type,
                    togther_collabcard.date_time,
                    togther_collabcard.is_pending,
                    togther_collabcard.attending_count,
                    togther_collabcard.polls_count,
                    togther_collabcard.date_epoch,
                    togther_collabcard.user_id,
                    togther_collabcard.has_been_named,
                    togther_collabcard.header,
                    togther_collabcardState.state,
                    togther_collabcardState.mute_status,
                    togther_collabcardState.follow_status,
                    togther_collabcard.access_without_subscription,
                    togther_collabcardState.is_tagged,
                    togther_collabcardState.last_seen_conversation_id,
                    togther_collabcardState.expiry_time,
                    togther_collabcardState.attending_status,
                    togther_collabcard.has_files,
                    togther_collabcard.is_poll_anonymous,
                    togther_collabcard.allow_add_option,
                    togther_collabcard.multiple_select_state,
                    togther_collabcard.multiple_select_no,
                    togther_collabcard.is_poll_anonymous,
                    togther_collabcard.poll_type,
                    togther_collabcard.end_date,
                    togther_collabcard.about,
                    togther_collabcard.co_hosts,
                    togther_collabcard.online_link,
                    togther_collabcard.og_tags,
                    togther_collabcard.internal_link,
                    togther_collabcard.deleted_by_user_id,
                    togther_collabcardState.updated_at,
                    togther_community.name,
                    togther_collabcard.duration,
                    togther_collabcard.location,
                    togther_collabcard.location_lat,
                    togther_collabcard.location_long,
                    togther_collabcard.attachment_count,
                    togther_collabcard.attachments_uploaded,
                    togther_collabcard.is_secret,
                    togther_collabcard.secret_chatroom_participants,
                    togther_collabcardState.secret_chatroom_left,
                    togther_collabcard.has_reactions,
                    togther_collabcard.device_id,
                    togther_collabcard.topic_id,
                    togther_collabcard.auto_follow_done,
                    togther_collabcard.is_edited,
                    togther_collabcard.online_link_enable_before,
                    togther_collabcard.online_link_id,
                    togther_collabcard.online_link_password,
                    togther_collabcard.is_paid,
                    togther_collabcard.access,
                    togther_collabcard.event_payment_link,
                    togther_collabcard.event_web_page,
                    togther_collabcardState.attended,
                    togther_collabcard.webflow_item_id,
                    togther_collabcard.is_private,
                    togther_collabcard.chatroom_with_user_id,
                    togther_collabcard.member_can_message,
                    togther_collabcardState.external_seen,
                    togther_collabcard.online_link_type,
                    togther_collabcard.is_private_member,
                    togther_collabcardState.chat_request_state,
                    togther_collabcardState.chat_requested_by_id,
                    togther_collabcardState.chat_request_created_at,
                    togther_collabcard.chatroom_image_url,
                    togther_collabcard.event_kind
                """

    return meta_query


def get_conversation_query_meta_for_sync():
    meta_query = """id,
                    answer,
                    created_at,
                    state,
                    is_edited,
                    has_files,
                    attachment_count,
                    attachments_uploaded,
                    card_id,
                    user_id,
                    community_id,
                    og_tags,
                    deleted_by_user_id,
                    internal_link,
                    reply_id,
                    last_updated,
                    preview_chatroom_id,
                    preview_type,
                    api_version,
                    temporary_id,
                    poll_type,
                    multiple_select_state,
                    multiple_select_no,
                    is_anonymous,
                    allow_add_option,
                    expiry_time,
                    preview_community_id,
                    has_reactions,
                    device_id,
                    poll_answer_text,
                    reply_chatroom_id,
                    header,
                    location,
                    location_lat,
                    location_long,
                    start_time,
                    end_time,
                    online_link_enable_before,
                    co_hosts
                    """

    return meta_query


def fetch_chatroom_polls(chatroom_id_list):
    '''function to update chatroom data'''

    try:
        conn = get_connection()
        curr = conn.cursor()

        if len(chatroom_id_list) == 1:
            chatroom_ids = "(" + str(chatroom_id_list[0]) + ")"
        else:
            chatroom_ids = tuple(chatroom_id_list)
        sql = """
        SELECT togther_collabcardPolls.card_id,
               togther_collabcardPolls.id,
               togther_collabcardPolls.text,
               togther_collabcardPolls.image_url,
               togther_collabcardPolls.sub_text,
               togther_collabcardPolls.user_id,
               togther_userinfo.name,
               togther_userinfo.image_link
        FROM togther_collabcardPolls
        INNER JOIN togther_userinfo
            ON togther_collabcardPolls.user_id = togther_userinfo.user_id_id
        WHERE togther_collabcardPolls.card_id IN %s
        ORDER BY  togther_collabcardPolls.id
            """ % (str(chatroom_ids))

        curr.execute(sql)

        data = curr.fetchall()
        curr.close()
        poll_data = {}
        for poll in data:
            card_id = poll[0]
            if poll[0] not in poll_data:
                temp = {
                    'id': poll[1],
                    'text': poll[2]
                }
                if poll[3]:
                    temp['image_url'] = poll[3]
                if poll[4]:
                    temp['sub_text'] = poll[4]
                temp['member'] = {
                    'id': poll[5],
                    'name': poll[6],
                    'image_url': poll[7]

                }
                poll_data[card_id] = [temp]

            else:
                temp = {
                    'id': poll[1],
                    'text': poll[2]
                }
                if poll[3]:
                    temp['image_url'] = poll[3]
                if poll[4]:
                    temp['sub_text'] = poll[4]
                temp['member'] = {
                    'id': poll[5],
                    'name': poll[6],
                    'image_url': poll[7]

                }
                poll_data[card_id].append(temp)

        return poll_data


    except (Exception, psycopg2.Error) as error:
        info_logger.info("Error while connecting to PostgreSQL  ", error)


def fetch_member_poll_votes(chatroom_id_list):
    try:
        conn = get_connection()
        curr = conn.cursor()
        if len(chatroom_id_list) == 1:
            chatroom_ids = "(" + str(chatroom_id_list[0]) + ")"
        else:
            chatroom_ids = tuple(chatroom_id_list)

        sql = """
        SELECT card_id,
               poll_id,
               user_id
        FROM togther_memberPollVotes
        WHERE card_id IN %s
        
        """ % (
            str(chatroom_ids))
        curr.execute(sql)
        data = curr.fetchall()
        curr.close()
        vote_dict = {}

        for vote in data:

            card_id = vote[0]
            if card_id not in vote_dict:
                temp = {
                    'card_id': vote[0],
                    'poll_id': vote[1],
                    'user_id': vote[2]
                }
                vote_dict[card_id] = [temp]
            else:
                temp = {
                    'card_id': vote[0],
                    'poll_id': vote[1],
                    'user_id': vote[2]
                }
                vote_dict[card_id].append(temp)

        return vote_dict


    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def fetch_chatroom_id_query(chatroom_id, user_id, last_updated=0, expired_member_ids=[]):
    try:
        conn = get_connection()
        curr = conn.cursor()

        if expired_member_ids:
            expired_member_list = "(togther_collabcardState.remove_id in ({}) OR togther_collabcardState.remove_id is NULL)" \
                                  "".format(",".join([str(i) for i in expired_member_ids]))

        else:
            expired_member_list = "togther_collabcardState.remove_id is NULL"

        sql = """
        SELECT %s
        FROM togther_collabcard
        INNER JOIN togther_collabcardState
            ON togther_collabcardState.card_id = togther_collabcard.id
        INNER JOIN togther_community
            ON togther_community.id = togther_collabcard.community_id
        WHERE togther_collabcardState.user_id=%s
                AND togther_collabcardState.card_id=%s
                AND %s
                AND togther_collabcardState.updated_at > %s
        
        """ % (get_chatroom_query_meta_for_sync(),
               str(user_id), str(chatroom_id), str(expired_member_list), str(last_updated))

        curr.execute(sql)
        data = curr.fetchall()
        curr.close()
        chatroom_id_list = get_chatroom_id_list(data)

        return data, chatroom_id_list

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s", error)


def fetch_community_chatroom_query(community_id, user_id, page, limit, last_updated, follow_status, type_list):
    try:
        conn = get_connection()
        curr = conn.cursor()

        offset = (int(page) - 1) * int(limit)

        type_tuple = get_tuple_from_array(type_list)

        if not type_tuple:
            return []

        sql = """
        SELECT %s
    FROM togther_collabcard
    INNER JOIN togther_collabcardState
        ON togther_collabcardState.card_id = togther_collabcard.id
    INNER JOIN togther_community
        ON togther_community.id = togther_collabcard.community_id
    WHERE togther_collabcard.community_id=%s
            AND togther_collabcardState.user_id = %s
            AND togther_collabcardState.updated_at > %s
            AND togther_collabcardState.remove_id is NULL
            AND togther_collabcardState.follow_status = %s
            AND togther_collabcard.type in %s
    ORDER BY  togther_collabcardState.updated_at limit %s offset %s
    
    """ % (get_chatroom_query_meta_for_sync(),
           str(community_id), str(user_id), str(last_updated), str(follow_status), str(type_tuple), str(limit),
           str(offset))

        curr.execute(sql)
        data = curr.fetchall()
        curr.close()

        chatroom_id_list = get_chatroom_id_list(data)

        return data, chatroom_id_list
    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  %s", error)

        return [], []


def fetch_chatrooms_query(user_id, limit, page, last_updated, type_list):
    '''function to update chatroom data'''

    try:
        conn = get_connection()
        curr = conn.cursor()

        offset = (int(page) - 1) * int(limit)

        type_tuple = get_tuple_from_array(type_list)

        if not type_tuple:
            return []

        last_updated = int(last_updated)

        sql = """
            SELECT %s
            FROM togther_collabcard
            INNER JOIN togther_collabcardState
                ON togther_collabcardState.card_id = togther_collabcard.id
            INNER JOIN togther_community
                ON togther_community.id = togther_collabcard.community_id
            WHERE togther_collabcardState.user_id=%s
                    AND togther_collabcardState.updated_at > %s
                    AND togther_collabcardState.remove_id is NULL
                    AND togther_collabcard.type in %s
            ORDER BY  togther_collabcardState.updated_at limit %s offset %s

                """ % (
            get_chatroom_query_meta_for_sync(), str(user_id), str(last_updated), str(type_tuple), str(limit),
            str(offset))

        curr.execute(sql)
        data = curr.fetchall()
        curr.close()
        chatroom_id_list = get_chatroom_id_list(data)

        return data, chatroom_id_list

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_chatroom_id_list(data):
    chatroom_id_list = []
    for card in data:
        if card[8] == card_types.CARD_POLL:
            chatroom_id_list.append(card[0])

    return chatroom_id_list


def get_event_chatroom_id_list(data):
    event_chatroom_ids = []

    for card in data:
        if card[8] in [card_types.CARD_EVENT, card_types.CARD_PUBLIC_EVENT]:
            event_chatroom_ids.append(card[0])

    return event_chatroom_ids


def get_community_id_list(member_id):
    """function to give community id list of member"""

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = """SELECT community_id_id
                    FROM togther_members
                    WHERE member_id_id=%s
              
              """ % (str(member_id))
        curr.execute(sql)
        data = curr.fetchall()
        curr.close()
        community_id_set = set()

        for community_id in data:
            community_id_set.add(community_id[0])

        guest_community_list = get_community_id_of_guest(member_id)

        for community_id in guest_community_list:
            community_id_set.add(community_id)

        return list(community_id_set)

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s", error)


def get_community_id_of_guest(member_id):
    """function to get community id for which the user id guest"""

    try:
        conn = get_connection()
        curr = conn.cursor()

        sql = """
        SELECT distinct(community_id)
        FROM togther_collabcardState
        WHERE is_guest=True
                AND user_id=%s
        """ % (str(member_id))
        curr.execute(sql)
        data = curr.fetchall()
        curr.close()
        guest_community_id_list = []

        for community_id in data:
            guest_community_id_list.append(community_id[0])

        return guest_community_id_list

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s", error)


def get_members_of_community_based_on_community_list_for_sync(community_id_list, last_updated, page, limit):
    """function to get members of the community present in community_id list"""

    try:
        conn = get_connection()
        curr = conn.cursor()
        community_id_tupple = get_tuple_from_array(community_id_list)

        if not community_id_tupple:
            return []

        offset = (int(page) - 1) * int(limit)

        sql = """SELECT togther_members.member_id_id,
                     togther_members.community_id_id,
                     togther_members.state,
                     togther_members.created_at,
                     togther_members.updated_at,
                     togther_members.is_owner,
                     togther_members.image_url,
                     togther_userinfo.image_link,
                     togther_userinfo.name,
                     togther_members.custom_title,
                     togther_community.name,
                     togther_userinfo.is_guest
            FROM togther_members
            INNER JOIN togther_userinfo
                ON togther_members.member_id_id = togther_userinfo.user_id_id
            INNER JOIN togther_community
                ON togther_community.id = togther_members.community_id_id
            WHERE togther_members.community_id_id IN %s
                    AND togther_members.updated_at > %s order by 
                    togther_members.updated_at, togther_members.id limit %s offset %s
            
            """ % (str(community_id_tupple), last_updated, limit, offset)

        curr.execute(sql)
        curr.execute(sql)
        res = curr.fetchall()
        curr.close()
        member_date = process_member_data(res)

        return member_date

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  %s", error)


def get_members_of_community_based_on_user_list_for_sync(user_id_list, community_id, last_updated, page, limit):
    try:
        conn = get_connection()
        curr = conn.cursor()
        user_id_tuple = get_tuple_from_array(user_id_list)

        if not user_id_tuple:
            return []

        offset = (int(page) - 1) * int(limit)

        sql = """SELECT togther_members.member_id_id,
                     togther_members.community_id_id,
                     togther_members.state,
                     togther_members.created_at,
                     togther_members.updated_at,
                     togther_members.is_owner,
                     togther_members.image_url,
                     togther_userinfo.image_link,
                     togther_userinfo.name,
                     togther_members.custom_title,
                     togther_community.name,
                     togther_userinfo.is_guest
            FROM togther_members
            INNER JOIN togther_userinfo
                ON togther_members.member_id_id = togther_userinfo.user_id_id
            INNER JOIN togther_community
                ON togther_community.id = togther_members.community_id_id
            WHERE togther_members.member_id_id IN %s
                    AND togther_members.updated_at > %s 
                    AND togther_members.community_id_id = %s order by updated_at, togther_members.id limit %s offset %s

            """ % (str(user_id_tuple), last_updated, str(community_id), limit, offset)

        curr.execute(sql)
        curr.execute(sql)
        res = curr.fetchall()
        curr.close()
        member_date = process_member_data(res)

        return member_date

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  %s", error)

        return {}


def get_member_responses_for_community(community_id_list):
    """check if member has responses in the community and returns a dictionary"""

    try:
        conn = get_connection()
        curr = conn.cursor()
        community_id_tupple = get_tuple_from_array(community_id_list)

        if not community_id_tupple:
            return {}

        sql = """
            SELECT member_id,
                   community_id
            FROM togther_communityAnswers
            WHERE community_id IN %s 
            """ % (
            str(community_id_tupple))
        curr.execute(sql)
        curr.execute(sql)
        res = curr.fetchall()
        curr.close()
        responses_dict = get_dictionary_of_member_responses(res)

        return responses_dict

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def process_member_data(res):
    """returns a list of dictionary containing information about member"""
    member_data = []

    for data in res:
        temp = dict()
        temp['member_id'] = data[0]
        temp['community_id'] = data[1]
        temp['state'] = data[2]
        temp['created_at'] = data[3]
        temp['updated_at'] = data[4]
        temp['is_owner'] = data[5]
        if data[6]:
            temp['image_url'] = data[6]
        elif data[7]:
            temp['image_url'] = data[7]
        else:
            temp['image_url'] = ""
        temp['name'] = data[8]
        temp['custom_title'] = data[9]
        temp['community_name'] = data[10]
        temp['is_guest'] = data[11]
        member_data.append(temp)

    return member_data


def get_tuple_from_array(array):
    if len(array) == 1:
        tupp = "(" + str(array[0]) + ")"

    else:
        tupp = tuple(array)

    return tupp


def get_tuple_from_array_v2(array):
    if len(array) == 1:
        tupp = "('" + str(array[0]) + "')"

    else:
        tupp = tuple(array)

    return tupp


def get_dictionary_of_member_responses(res):
    responses_dict = dict()

    for data in res:
        member_id = data[0]
        community_id = data[1]
        key = str(member_id) + "$" + str(community_id)

        if key not in responses_dict:
            responses_dict[key] = True

    return responses_dict

def process_users_meta_data_from_query_response(users_data: list, list_only: bool = False):
    """ This method processes users data by splitting data using a defined key."""
    
    users_dict = {}
    users_meta = []

    for user in users_data:
        parsed_user_data = {}

        sdk_client_info_null = False

        for key in user:
            split_keys = key.split('___') 

            if len(split_keys) == 2:
                if not parsed_user_data.get(split_keys[0]):
                    parsed_user_data[split_keys[0]] = {}

                parsed_user_data[split_keys[0]][split_keys[1]] = user[key]

                if split_keys[0] == 'sdk_client_info' and user[key] is None:
                    sdk_client_info_null = True
            else:
                parsed_user_data[key] = user[key]
        
        if sdk_client_info_null:
            parsed_user_data['sdk_client_info'] = None

        if parsed_user_data.get('id'):
            users_dict[parsed_user_data['id']] = parsed_user_data

        # For sdk_client_info support, as it has user instead of id as key
        elif parsed_user_data.get('user'):
            users_dict[parsed_user_data['user']] = parsed_user_data
        
        if list_only:
            users_meta.append(parsed_user_data)

    if list_only:
        return users_meta
    
    return users_dict


def get_users_sdk_meta_dict(user_ids: list, only_sdk_client_info: bool = False) -> dict:
    """ This method fetches the users data along with its client_user_unique_id using raw query.
        It returns a dict with user_id as key and user_meta as value.
    """
    users_dict = {}

    try:
        user_id_tuple = get_tuple_from_array(user_ids)

        if not user_id_tuple:
            return users_dict

        if only_sdk_client_info:
            sql = f"""
                SELECT  togther_sdkclientusersinfo.user_id          AS "user",
                        togther_sdkclientusersinfo.user_unique_id   AS "user_unique_id",
                        togther_sdkclientusersinfo.user_unique_id   AS "uuid",
                        togther_sdkclientusersinfo.community_id     AS "community",
                        togther_sdkclientusersinfo.widget_id        AS "widget_id"
                FROM    togther_sdkclientusersinfo

                WHERE   togther_sdkclientusersinfo.user_id IN {user_id_tuple};
            """

        else:
            sql = f"""
                    SELECT
                    togther_userinfo.user_id_id                 AS "id",
                    togther_userinfo.image_link                 AS "image_url",
                    togther_userinfo.is_guest                   AS "is_guest",
                    togther_userinfo.name                       AS "name",
                    togther_userinfo.organisation_name          AS "organisation_name",
                    togther_userinfo.updated_at                 AS "updated_at",
                    togther_userinfo.user_unique_id             AS "user_unique_id",
                    togther_userinfo.user_unique_id             AS "uuid",
                    togther_sdkclientusersinfo.user_id          AS "sdk_client_info___user",
                    togther_sdkclientusersinfo.user_unique_id   AS "sdk_client_info___user_unique_id",
                    togther_sdkclientusersinfo.user_unique_id   AS "sdk_client_info___uuid",
                    togther_sdkclientusersinfo.community_id     AS "sdk_client_info___community",
                    togther_sdkclientusersinfo.widget_id        AS "sdk_client_info___widget_id"

                    FROM togther_userinfo
                    LEFT JOIN togther_sdkclientusersinfo
                    ON togther_sdkclientusersinfo.user_id = togther_userinfo.user_id_id
    
                    WHERE togther_userinfo.user_id_id IN {user_id_tuple};
            """
            
        conn = get_connection()
        curr = conn.cursor()

        curr.execute(sql)

        query_result = convert_sql_query_result_to_dict(curr, curr.fetchall())
        curr.close()

        # Process the users data for key(id): value(data) pair
        users_dict = process_users_meta_data_from_query_response(query_result)

        return users_dict
    
    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)

        return users_dict


def fetch_chatroom_query_with_follow_status(user_id, limit, page, last_updated, follow_status, type_list):
    """function to update chatroom data"""

    try:
        conn = get_connection()
        curr = conn.cursor()

        offset = (int(page) - 1) * int(limit)

        type_tuple = get_tuple_from_array(type_list)

        if not type_tuple:
            return []

        last_updated = int(last_updated)

        sql = """
        SELECT %s
        FROM togther_collabcard
        INNER JOIN togther_collabcardState
            ON togther_collabcardState.card_id = togther_collabcard.id
        INNER JOIN togther_community
            ON togther_community.id = togther_collabcard.community_id
        WHERE togther_collabcardState.user_id=%s
                AND togther_collabcardState.updated_at > %s
                AND follow_status = %s
                AND togther_collabcardState.remove_id is NULL
                AND togther_collabcard.type in %s
        ORDER BY  togther_collabcardState.updated_at limit %s offset %s
        
            """ % (get_chatroom_query_meta_for_sync(),
                   str(user_id), str(last_updated), follow_status, str(type_tuple), str(limit), str(offset))
        curr.execute(sql)
        data = curr.fetchall()
        curr.close()
        chatroom_id_list = get_chatroom_id_list(data)

        return data, chatroom_id_list

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def fetch_chatroom_with_videos(limit, page, card_list):
    """function to update chatroom data"""

    try:
        conn = get_connection()
        curr = conn.cursor()

        offset = (int(page) - 1) * int(limit)

        if len(card_list) > 1:
            card_list = str(card_list)
        else:
            card_list = f"({card_list[0]})"

        sql = """SELECT distinct on (togther_collabcard.id)
                    %s
                FROM togther_collabcard
                INNER JOIN togther_collabcardState
                    ON togther_collabcardState.card_id = togther_collabcard.id
                INNER JOIN togther_community
                    ON togther_community.id = togther_collabcard.community_id
                WHERE togther_collabcard.id IN %s
                ORDER BY  togther_collabcard.id limit %s offset %s """ % (
            get_chatroom_query_meta_for_sync(),
            str(card_list), str(limit), str(offset))

        curr.execute(sql)
        data = curr.fetchall()
        curr.close()
        chatroom_id_list = get_chatroom_id_list(data)

        return data, chatroom_id_list

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_conversation_data_based_on_chatroom_list(chatroom_list, page, limit, last_updated, state):
    """
    return the conversations of chatrooms based on chatroom list
    """
    try:
        conn = get_connection()
        curr = conn.cursor()
        offset = (int(page) - 1) * int(limit)
        last_updated = int(last_updated)
        chatroom_id_tupple = get_tuple_from_array(chatroom_list)

        if not chatroom_id_tupple:
            return [], []

        if state:
            sql = """SELECT %s
                    FROM togther_card_answers
                    WHERE last_updated > %s
                            AND card_id IN %s
                            AND state=%s
                    ORDER BY  last_updated limit %s offset %s
                   """ % (
                get_conversation_query_meta_for_sync(), str(last_updated), str(chatroom_id_tupple),
                str(state), str(limit),
                str(offset))

        else:
            sql = """SELECT %s
                    FROM togther_card_answers
                    WHERE last_updated > %s
                            AND card_id IN %s
                    ORDER BY  last_updated limit %s offset %s
                   """ % (
                get_conversation_query_meta_for_sync(), str(last_updated), str(chatroom_id_tupple), str(limit),
                str(offset))

        curr.execute(sql)
        data = curr.fetchall()
        curr.close()

        files_answer_id = []

        for ans in data:

            if ans[5]:
                files_answer_id.append(ans[0])

        return data, files_answer_id

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)

        return [], []


def get_community_conversation_data_based_on_chatroom_list(chatroom_list, page, limit, last_updated, community_id,
                                                           state):
    """
    return the conversations of chatrooms based on chatroom list
    """
    try:
        conn = get_connection()
        curr = conn.cursor()
        offset = (int(page) - 1) * int(limit)
        last_updated = int(last_updated)
        chatroom_id_tupple = get_tuple_from_array(chatroom_list)

        if not chatroom_id_tupple:
            return [], []

        if state:
            sql = """SELECT %s
                    FROM togther_card_answers
                    WHERE last_updated > %s
                            AND card_id IN %s
                            AND community_id = %s
                            AND state=%s
                    ORDER BY  last_updated limit %s offset %s
                   """ % (
                get_conversation_query_meta_for_sync(), str(last_updated), str(chatroom_id_tupple),
                str(community_id), str(state),
                str(limit), str(offset))

        else:
            sql = """SELECT %s
                              FROM togther_card_answers
                              WHERE last_updated > %s
                                      AND card_id IN %s
                                      AND community_id = %s
                              ORDER BY  last_updated limit %s offset %s
                             """ % (
                get_conversation_query_meta_for_sync(), str(last_updated), str(chatroom_id_tupple), str(community_id),
                str(limit), str(offset))
        curr.execute(sql)
        data = curr.fetchall()
        curr.close()

        files_answer_id = []

        for ans in data:

            if ans[5]:
                files_answer_id.append(ans[0])

        return data, files_answer_id

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)

        return [], []


def get_conversation_files_based_on_conversation_list(conversation_list):
    """The function returns a dictionary containing files based on answer id"""

    try:
        conn = get_connection()
        curr = conn.cursor()
        conversation_id_tupple = get_tuple_from_array(conversation_list)
        conversation_files_dict = dict()

        if not conversation_id_tupple:
            return {}

        sql = """select  
                        answer_id,
                        file_url,
                        type,
                        location_name,
                        location_lat,
                        location_long,
                        index,
                        height,
                        width,
                        thumbnail_url,
                        name,
                        meta
               from togther_answerAttachment  where answer_id  in %s order by id 
               """ % (str(conversation_id_tupple))

        curr.execute(sql)
        data = curr.fetchall()
        curr.close()

        for file in data:

            conversation_id = file[0]

            if conversation_id not in conversation_files_dict:
                temp = {
                    'file_url': file[1],
                    'type': file[2],
                    'location_name': file[3],
                    'location_lat': file[4],
                    'location_long': file[5],
                    'index': file[6],
                    'height': file[7],
                    'width': file[8],
                    'thumbnail_url': file[9],
                    'name': file[10],
                    'meta': file[11]
                }

                conversation_files_dict[conversation_id] = [temp]

            else:
                temp = {
                    'file_url': file[1],
                    'type': file[2],
                    'location_name': file[3],
                    'location_lat': file[4],
                    'location_long': file[5],
                    'index': file[6],
                    'height': file[7],
                    'width': file[8],
                    'thumbnail_url': file[9],
                    'name': file[10],
                    'meta': file[11]
                }
                conversation_files_dict[conversation_id].append(temp)

        return conversation_files_dict

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)

        return {}


def get_members_based_on_user_list_query(user_list, community_id, order_by_name=False, page=0, page_size=0,
                                         member_name_search_string=""):
    """returns the members of the community based on user list"""

    try:
        conn = get_connection()
        curr = conn.cursor()
        user_tupple = get_tuple_from_array(user_list)

        if not user_tupple:
            return []

        sql = """SELECT "togther_members"."member_id_id",
                         "togther_members"."community_id_id",
                         "togther_members"."state",
                         "togther_members"."image_url",
                         "togther_members"."is_owner",
                         "togther_members"."custom_title",
                         "togther_userinfo"."name",
                         "togther_userinfo"."image_link",
                         "togther_members"."created_at",
                         "togther_userinfo"."user_unique_id",
                         "togther_userinfo"."is_guest"
                FROM "togther_members"
                INNER JOIN "togther_userinfo"
                    ON ("togther_members"."member_id_id" = "togther_userinfo"."user_id_id")
                WHERE ("togther_members"."community_id_id" = %s
                        AND "togther_members"."member_id_id" IN %s)""" % (str(community_id), str(user_tupple))

        if member_name_search_string:
            sql += """ AND ("togther_userinfo"."name" ILIKE '%s')""" % str(member_name_search_string + "%")

        if order_by_name:
            sql += " order by lower(togther_userinfo.name) ASC, togther_userinfo.id"

        if page_size:
            sql += """ limit %s""" % str(page_size)

        if page:
            sql += """ offset %s""" % str((page - 1) * page_size)

        curr.execute(sql)
        member_data = curr.fetchall()
        curr.close()

        member_list = []

        for data in member_data:
            member_dict = dict()
            member_dict['member_id'] = data[0]
            member_dict['community_id'] = data[1]
            member_dict['state'] = data[2]
            member_dict['image_url'] = data[3]
            member_dict['is_owner'] = data[4]
            member_dict['custom_title'] = data[5]
            member_dict['name'] = data[6]
            member_dict['image_link'] = data[7]
            member_dict['created_at'] = data[8]
            member_dict['user_unique_id'] = data[9]
            member_dict['is_guest'] = data[10]
            member_list.append(member_dict)

        return member_list

    except (Exception, psycopg2.Error) as error:
        print(error)
        error_logger.error("Error while connecting to PostgreSQL %s ", error)

        return []


def get_members_meta_list(community_id: int, member_ids: list = None, page=1, page_size=50, search_string: str = ''):
    """returns meta data of members based on community_id and or member_ids"""

    try:

        page_number = int(page)
        offset = (page_number - 1) * page_size

        get_removed_members = ""
        join_removed_members_table = ""

        # If member_ids are passed get users from the user_ids and join removedMembers table
        if member_ids:  
            user_ids = get_tuple_from_array(member_ids)

            join_removed_members_table = f"""
                                                left join togther_removedmembers 
                                                on (togther_userinfo.user_id_id = togther_removedmembers.member_id
                                                AND togther_removedmembers.community_id = {community_id})
                                          """
            
            get_removed_members = f""" 
                                    And togther_members.member_id_id in {user_ids}
                                    or togther_removedmembers.community_id = {community_id}
                                    And togther_removedmembers.member_id in {user_ids}
                                    """

        # select query for members meta 
        members_meta_data_query = get_query_fields_for_members_meta()

        # Sql Query
        sql = f""" 
               select 
                {members_meta_data_query}, 
                togther_userinfo.user_unique_id as "uuid",
                togther_userinfo.user_id_id as "id", 
                togther_userinfo.image_link as "image_url", 
                CASE when (togther_members.custom_title = 'Member') then Null else togther_members.custom_title END as "custom_title", 
                CASE when (togther_members.community_id_id = {community_id}) then false else true END as "is_deleted",
                togther_sdkclientusersinfo.user_unique_id as "sdk_client_info___user_unique_id",
                togther_sdkclientusersinfo.user_unique_id as "sdk_client_info___uuid",
                togther_sdkclientusersinfo.community_id as "sdk_client_info___community",
                togther_sdkclientusersinfo.user_id as "sdk_client_info___user",
                togther_sdkclientusersinfo.widget_id as "sdk_client_info___widget_id"

                from  togther_userinfo
                left join togther_members 
                on (togther_userinfo.user_id_id = togther_members.member_id_id AND togther_members.community_id_id = {community_id})
                left join togther_sdkclientusersinfo 
                on (togther_sdkclientusersinfo.user_id = togther_userinfo.user_id_id AND togther_sdkclientusersinfo.community_id = {community_id})
                {join_removed_members_table}

                where
                    togther_userinfo.is_guest is false
                    And togther_members.community_id_id = {community_id} 
                    And togther_members.state in (1,4,9)
                    {get_removed_members}
                    AND ("togther_userinfo"."name" ILIKE '{search_string}%')

                order by lower(togther_userinfo.name) ASC, togther_userinfo.id
                OFFSET {offset} LIMIT {page_size};
              """

        conn = get_connection()
        curr = conn.cursor()

        curr.execute(sql)

        # Map query result to column names
        query_result = convert_sql_query_result_to_dict(curr, curr.fetchall())
        curr.close()

        users_meta = process_users_meta_data_from_query_response(query_result, list_only=True)

        return users_meta
    
    except (Exception, psycopg2.Error) as error:
        print(error)
        error_logger.error("Error while running query: %s ", error)

        return []


def get_community_introductions_based_on_user_list_query(user_list, community_id, question_id) -> list:
    try:
        conn = get_connection()
        curr = conn.cursor()
        user_tupple = get_tuple_from_array(user_list)

        if not user_tupple:
            return []

        sql = """
       SELECT togther_communityAnswers.member_id,
                 togther_communityAnswers.community_id,
                 togther_communityAnswers.question_answer,
                 togther_communityAnswers.question_title
       FROM togther_communityAnswers
       WHERE togther_communityAnswers.community_id=%s
                AND member_id IN  %s
                AND question_id = %s
                """ % \
              (str(community_id), str(user_tupple), str(question_id))

        curr.execute(sql)
        member_data = curr.fetchall()
        curr.close()

        return member_data

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)
        return []


def activate_chatroom_on_conversation_creation(card_id, user_id):
    """function to set active time after new conversation created"""

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = """UPDATE togther_collabcardState SET expiry_time = null, updated_at=%s
                 WHERE  card_id=%s
                        AND follow_status=True
                        AND remove_id is null
                        AND user_id!=%s """ % (str(TimeUtilities.current_time_in_sec()), str(card_id), str(user_id))

        curr.execute(sql)
        conn.commit()

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_latest_conversation_creator_users_for_homescreen(chatroom_id, chatroom_creator_id):
    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = """SELECT DISTINCT user_id,
                MAX(created_at)
                FROM togther_card_answers
                WHERE card_id=%s
                        AND user_id!=%s
                GROUP BY  user_id
                ORDER BY  MAX(created_at) DESC limit 2 """ % (str(chatroom_id), str(chatroom_creator_id))

        curr.execute(sql)
        members_data = curr.fetchall()
        curr.close()
        user_list = []

        for user in members_data:
            user_list.append(user[0])

        return user_list

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)
        return []


def get_chatroom_count_based_on_community_list(community_id_list, member_id, excluded_card_ids=None) -> {}:
    try:
        conn = get_connection()
        curr = conn.cursor()

        community_id_tupple = get_tuple_from_array(community_id_list)

        excluded_card_ids_list = ""

        if excluded_card_ids:
            excluded_card_ids_list = 'AND ("togther_collabcard"."id" NOT IN {})'.format(
                get_tuple_from_array(excluded_card_ids))

        if not community_id_tupple:
            return {}

        sql = """SELECT "togther_collabcardstate".community_id,
                         COUNT(*) AS "__count"
                FROM "togther_collabcardstate"
                INNER JOIN "togther_collabcard"
                    ON ("togther_collabcardstate"."card_id" = "togther_collabcard"."id")
                WHERE ("togther_collabcard"."is_deleted" = FALSE
                        AND "togther_collabcardstate"."secret_chatroom_left" = FALSE
                        AND "togther_collabcardstate"."user_id" = %s
                        AND NOT ("togther_collabcard"."type" in (%s, %s, %s, %s))
                        AND ("togther_collabcard"."is_private" = FALSE)
                        AND ("togther_collabcard"."is_pending" = FALSE)
                        AND ("togther_collabcard"."chatroom_with_user_id" is NULL)
                        %s)
                GROUP BY  togther_collabcardstate.community_id
                HAVING "togther_collabcardstate".community_id IN %s""" \
              % (str(member_id), str(card_types.CARD_INTRO), str(card_types.CARD_EVENT),
                 str(card_types.CARD_PUBLIC_EVENT), str(card_types.CARD_FEED_GROUP), excluded_card_ids_list, str(community_id_tupple))

        curr.execute(sql)
        count_data = curr.fetchall()
        curr.close()

        community_count_group = {}

        for data in count_data:
            community_count_group[data[0]] = data[1]

        return community_count_group

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)

        return {}


def get_count_of_community_members_based_on_community_list(community_id_list) -> {}:
    try:
        conn = get_connection()
        curr = conn.cursor()

        community_id_tupple = get_tuple_from_array(community_id_list)

        if not community_id_tupple:
            return {}

        sql = """SELECT community_id_id,
                count(*)
                FROM togther_members
                WHERE community_id_id IN %s
                        AND (state=1
                        OR state=4
                        OR state=9)
                GROUP BY  community_id_id""" \
              % (str(community_id_tupple))

        curr.execute(sql)
        count_data = curr.fetchall()
        curr.close()

        community_count_group = {}

        for data in count_data:
            community_count_group[data[0]] = data[1]

        return community_count_group

    except Exception as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)

        return {}


def get_distinct_chatroom_creator_list(community_id, member_id) -> []:
    try:
        conn = get_connection()
        curr = conn.cursor()

        sql = """
           SELECT DISTINCT user_id,
                  MAX(date_epoch)
           FROM togther_collabcard
           WHERE community_id =%s
                    AND type!=1
                    AND is_deleted=False
                    AND
                (CASE
                WHEN is_secret=True
                    AND secret_chatroom_participants LIKE '%s' THEN
                True
                WHEN is_secret=True THEN
                False
                WHEN is_secret=False THEN
                True
                END)
           GROUP BY  user_id
           ORDER BY  MAX(date_epoch) DESC limit 4 
        """ % (str(community_id), "%" + str(member_id) + "%")

        curr.execute(sql)
        user_data = curr.fetchall()
        curr.close()

        user_list = []

        for data in user_data:
            user_list.append(data[0])

        return user_list

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)

        return []


def get_recent_n_days_conversation_chatroom_list(community_id, duration, limit) -> []:
    """returns the recent n days card id list"""

    try:
        conn = get_connection()
        curr = conn.cursor()

        sql = """
           SELECT DISTINCT card_id,
                     MAX(created_at)
           FROM togther_card_answers
           WHERE community_id=%s
                    AND card_id IN 
                (SELECT id
                FROM togther_collabcard
                WHERE (type!=%s
                        AND type!=%s
                        AND type!=%s
                        AND type!=%s))
            AND (state=0 or state=10)
            GROUP BY  card_id
            HAVING max(created_at) > %s
            ORDER BY  MAX(created_at) DESC limit %s 
        """ % (
            str(community_id), str(card_types.CARD_PURPOSE), str(card_types.CARD_INTRO),
            str(card_types.CARD_MASTER_INTRO), str(card_types.CARD_DIRECT_MESSAGE),
            str(duration), str(limit))

        curr.execute(sql)
        card_list = curr.fetchall()
        curr.close()

        return [data[0] for data in card_list]

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)

        return []


def get_n_percentage_member_conversation_chatroom_list(community_id, members_count, limit) -> []:
    """returns the recent chatrooms where n percentage of  members have created conversation"""

    try:
        conn = get_connection()
        curr = conn.cursor()

        sql = """
                SELECT card_id,
                 max(created_at)
        FROM togther_card_answers
        WHERE community_id=%s
                AND card_id IN 
            (SELECT id
            FROM togther_collabcard
            WHERE type!=%s
                    AND type!=%s
                    AND type!=%s
                    AND type!=%s)
            AND (state=0 or state=10)
        GROUP BY  card_id
        HAVING count(distinct(user_id)) > %s
        ORDER BY  max(created_at) DESC limit %s
        """ % (
            str(community_id), str(card_types.CARD_PURPOSE), str(card_types.CARD_INTRO),
            str(card_types.CARD_MASTER_INTRO), str(card_types.CARD_DIRECT_MESSAGE),
            str(members_count), str(limit))

        curr.execute(sql)
        card_list = curr.fetchall()
        curr.close()

        return [data[0] for data in card_list]

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)

        return []


def get_last_seen_event_chatroom_id_for_user(user_id, community_id: str = None):
    try:
        conn = get_connection()
        curr = conn.cursor()

        community_filter: str = str()
        if community_id:
            community_filter: str = f'AND community_id={community_id}'

        sql = """SELECT card_id
                 FROM togther_collabcardState
                 WHERE card_id IN 
                    (SELECT id
                    FROM togther_collabcard
                    WHERE type in (2,6) AND access in (1,2))
                        AND user_id=%s
                        %s
                 ORDER BY card_id desc limit 1
        """ % (
            str(user_id),
            community_filter
        )

        curr.execute(sql)
        card_tupple = curr.fetchone()
        curr.close()

        if card_tupple:
            return card_tupple[0]

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_last_seen_non_member_access_event_chatroom_id_for_community_managers(user_id, community_id: str = None):
    try:
        conn = get_connection()
        curr = conn.cursor()

        community_filter: str = str()
        if community_id:
            community_filter: str = f'AND community_id={community_id}'

        sql = """
                SELECT card_id
                FROM togther_collabcardState
                WHERE card_id IN (
                    SELECT id
                    FROM togther_collabcard
                    WHERE type IN (2,6)
                        AND (access = 0 OR access is NULL)
                        AND community_id IN (
                            SELECT community_id_id
                            FROM togther_members
                            WHERE user_id=%s
                                %s
                                AND state = 1
                        )
                    )
                    AND user_id=%s
                ORDER BY card_id DESC limit 1
        """ % (
            str(user_id),
            community_id,
            str(user_id)
        )

        curr.execute(sql)
        card_tuple = curr.fetchone()
        curr.close()

        if card_tuple:
            return card_tuple[0]

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_last_seen_non_member_access_event_for_user(user_id, community_id: str = None):
    try:
        conn = get_connection()
        curr = conn.cursor()

        community_filter: str = str()
        if community_id:
            community_filter: str = f'AND community_id={community_id}'

        sql = """
                SELECT card_id
                FROM togther_collabcardState
                WHERE card_id IN 
                    (SELECT id
                    FROM togther_Collabcard
                    WHERE type IN (2,6)
                            AND (access = 0 or access is NULL)
                            AND id IN 
                        (SELECT chatroom_id
                        FROM togther_ChatroomCohort
                        WHERE cohort_id IN 
                            (SELECT cohort_id
                            FROM togther_CohortMember
                            WHERE user_id = %s)))
                                AND user_id = %s
                                %s
                ORDER BY card_id DESC limit 1;
        """ % (
            str(user_id),
            str(user_id),
            community_filter
        )

        curr.execute(sql)
        card_tuple = curr.fetchone()
        curr.close()

        if card_tuple:
            return card_tuple[0]

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_count_of_new_event_chatrooms_created_for_user(card_id, user_id, community_id: str = None):
    try:
        conn = get_connection()
        curr = conn.cursor()

        community_filter: str = str()
        if community_id:
            community_filter: str = f'AND community_id={community_id}'

        sql = """SELECT count(*)
                 FROM togther_collabcardState
                 WHERE card_id IN 
                    (SELECT id
                    FROM togther_collabcard
                    WHERE type in (2,6) AND access in (1,2))
                        AND user_id=%s
                        %s
                 AND card_id > %s
        """ % (
            str(user_id),
            community_filter,
            str(card_id)
        )

        curr.execute(sql)
        card_tupple = curr.fetchone()
        curr.close()

        if card_tupple:
            return card_tupple[0]

        return 0

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_count_for_new_non_member_access_event_chatroom_community_managers(user_id, card_id, community_id: str = None):
    try:
        conn = get_connection()
        curr = conn.cursor()

        community_filter: str = str()
        if community_id:
            community_filter: str = f'AND community_id_id={community_id}'

        sql = """
                SELECT count(*)
                FROM togther_collabcardState
                WHERE card_id IN (
                    SELECT id
                    FROM togther_collabcard
                    WHERE type IN (2,6)
                        AND (
                            access = 0 
                            OR access is NULL
                        )
                        AND community_id IN (
                            SELECT community_id_id
                            FROM togther_members
                            WHERE user_id=%s
                            %s
                            AND state = 1
                        )
                    )
                    AND user_id=%s
                    AND card_id > %s
        """ % (
            str(user_id),
            community_filter,
            str(user_id),
            str(card_id)
        )

        curr.execute(sql)
        card_tuple = curr.fetchone()
        curr.close()

        if card_tuple:
            return card_tuple[0]
        return 0

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_count_for_non_member_access_event_for_user_non_community_manager(user_id, card_id, community_id: str = None):
    try:
        conn = get_connection()
        curr = conn.cursor()

        community_filter: str = str()
        if community_id:
            community_filter: str = f'AND community_id={community_id}'

        sql = """
                SELECT count(*)
                FROM togther_collabcardState
                WHERE card_id IN (
                    SELECT id
                    FROM togther_Collabcard
                    WHERE type IN (2,6)
                        AND (
                            access = 0 
                            or access is NULL
                        )
                        AND id IN (
                            SELECT chatroom_id
                            FROM togther_ChatroomCohort
                            WHERE cohort_id IN (
                                SELECT cohort_id
                                FROM togther_CohortMember
                                WHERE user_id = %s
                            )
                        )
                        AND community_id NOT IN (
                            SELECT community_id_id
                            FROM togther_members
                            WHERE user_id=%s
                                AND state = 1
                            )
                        )
                    AND user_id = %s
                    %s
                    AND card_id > %s
        """ % (
            str(user_id),
            str(user_id),
            str(user_id),
            community_filter,
            str(card_id))

        curr.execute(sql)
        card_tuple = curr.fetchone()
        curr.close()

        if card_tuple:
            return card_tuple[0]
        return 0

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_count_of_new_event_conversation_created_for_user(conversation_id, chatroom_list):
    try:
        conn = get_connection()
        curr = conn.cursor()

        card_tuple = get_tuple_from_array(chatroom_list)

        if not card_tuple:
            return 0

        sql = """SELECT count(*)
                 FROM togther_card_answers
                 WHERE id > %s
                 AND state = %s AND card_id in %s
        """ % (str(conversation_id), str(conversation_states.CONVERSATION_EVENT), str(card_tuple))
        curr.execute(sql)
        conversation_tuple = curr.fetchone()
        curr.close()

        if conversation_tuple:
            return conversation_tuple[0]

        return 0

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_last_seen_event_conversation_id_for_user(chatroom_list):
    try:
        conn = get_connection()
        curr = conn.cursor()

        card_tuple = get_tuple_from_array(chatroom_list)

        if not card_tuple:
            return 0

        sql = """SELECT id
                 FROM togther_card_answers
                 where state=%s and card_id in %s
                 ORDER BY id desc limit 1
        """ % (str(conversation_states.CONVERSATION_EVENT), str(card_tuple))
        curr.execute(sql)
        conversation_tuple = curr.fetchone()
        curr.close()

        if conversation_tuple:
            return conversation_tuple[0]

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def create_pinned_query_for_feed_revamp(default_pinned_query, is_pinned):

    if is_pinned:
        return default_pinned_query.format("true")

    return ""


def get_ordered_card_id_on_the_basis_of_message_count(user_id, community_id, is_pinned, excluded_card_ids,
                                                      excluded_card_types, page=1, limit=10):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        excluded_card_id_string = ""

        if excluded_card_ids:
            excluded_card_ids_tuple = get_tuple_from_array(excluded_card_ids)
            excluded_card_id_string = "AND CA.id NOT IN {}".format(excluded_card_ids_tuple)

        excluded_card_types_tuple = get_tuple_from_array(excluded_card_types)
        is_pinned = "true" if is_pinned else "false"

        conn = get_connection()
        curr = conn.cursor()

        sql = """
            SELECT    cs.card_id,
                      COALESCE(cs2.answer_count, 0) AS answer_count
            FROM      (
                                 SELECT     ca.id                   AS card_id
                                 FROM       togther_collabcardstate AS cs
                                 INNER JOIN togther_collabcard      AS ca
                                 ON         cs.card_id = ca.id
                                 WHERE      (
                                                       cs.secret_chatroom_left = false
                                            AND        ca.community_id = {}
                                            AND        ca.is_pending = false
                                            AND        ca.is_deleted = false
                                            AND        ca.is_private = false
                                            AND        ca.type NOT IN {}
                                            AND        ca.is_pinned = {}
                                            AND        cs.user_id = {} {} )) AS cs
            LEFT JOIN
                      (
                                SELECT    togther_collabcard.id               AS card_id,
                                          count(togther_card_answers.card_id) AS answer_count
                                FROM      togther_collabcard
                                LEFT JOIN togther_card_answers
                                ON        togther_collabcard.id = togther_card_answers.card_id
                                WHERE     togther_collabcard.id IN
                                          (
                                                     SELECT     ca.id
                                                     FROM       togther_collabcardstate AS cs
                                                     INNER JOIN togther_collabcard      AS ca
                                                     ON         cs.card_id = ca.id
                                                     WHERE      (
                                                                           cs.secret_chatroom_left = false
                                                                AND        ca.community_id = {}
                                                                AND        ca.is_pending = false
                                                                AND        ca.is_deleted = false
                                                                AND        ca.is_private = false
                                                                AND        ca.type NOT IN {}
                                                                AND        ca.is_pinned = {}
                                                                AND        cs.user_id = {} {} ))
                                AND       togther_card_answers.state IN (0)
                                AND       (
                                                    togther_card_answers.attachment_count = 0
                                          OR        togther_card_answers.attachments_uploaded = true )
                                GROUP BY  togther_collabcard.id) AS cs2
            ON        cs.card_id = cs2.card_id
            ORDER BY  answer_count DESC limit {} offset {}; 
        """.format(community_id, excluded_card_types_tuple, is_pinned, user_id, excluded_card_id_string,
                   community_id, excluded_card_types_tuple, is_pinned, user_id, excluded_card_id_string,
                   limit, offset)

        curr.execute(sql)
        res = curr.fetchall()
        curr.close()

        ordered_card_ids = []
        for card_id in res:
            ordered_card_ids.append(card_id[0])

        return ordered_card_ids

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_ordered_card_id_on_the_basis_of_message_count_v2(user_id, community_id, is_pinned, excluded_card_ids,
                                                         excluded_card_types, pinned_chatrooms_list, page=1, limit=10):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        excluded_card_id_string = ""

        if excluded_card_ids:
            excluded_card_ids_tuple = get_tuple_from_array(excluded_card_ids)
            excluded_card_id_string = "AND CA.id NOT IN {}".format(excluded_card_ids_tuple)

        excluded_card_types.append(card_types.CARD_FEED_GROUP)
        excluded_card_types_tuple = get_tuple_from_array(excluded_card_types)

        pinned_chatrooms_query = create_pinned_query_for_feed_revamp("AND ca.is_pinned = {}", is_pinned)

        order_by_query = "answer_count DESC"

        if (not is_pinned) and (len(pinned_chatrooms_list) <= MIN_NUMBER_OF_PIN_CHATROOMS_IN_FEED_REVAMP):
            order_by_query = "cs.is_pinned DESC, answer_count DESC"

        conn = get_connection()
        curr = conn.cursor()

        sql = """
            SELECT    cs.card_id,
                      COALESCE(cs2.answer_count, 0) AS answer_count
            FROM      (
                                 SELECT     ca.id AS card_id, ca.is_pinned
                                 FROM       togther_collabcardstate AS cs
                                 INNER JOIN togther_collabcard      AS ca
                                 ON         cs.card_id = ca.id
                                 WHERE      (
                                                       cs.secret_chatroom_left = false
                                            AND        ca.community_id = {}
                                            AND        ca.is_pending = false
                                            AND        ca.is_deleted = false
                                            AND        ca.is_private = false
                                            AND        ca.type NOT IN {}
                                            {}
                                            AND        cs.user_id = {} {} )) AS cs
            LEFT JOIN
                      (
                                SELECT    togther_collabcard.id               AS card_id,
                                          count(togther_card_answers.card_id) AS answer_count
                                FROM      togther_collabcard
                                LEFT JOIN togther_card_answers
                                ON        togther_collabcard.id = togther_card_answers.card_id
                                WHERE     togther_collabcard.id IN
                                          (
                                                     SELECT     ca.id
                                                     FROM       togther_collabcardstate AS cs
                                                     INNER JOIN togther_collabcard      AS ca
                                                     ON         cs.card_id = ca.id
                                                     WHERE      (
                                                                           cs.secret_chatroom_left = false
                                                                AND        ca.community_id = {}
                                                                AND        ca.is_pending = false
                                                                AND        ca.is_deleted = false
                                                                AND        ca.is_private = false
                                                                AND        ca.type NOT IN {}
                                                                {}
                                                                AND        cs.user_id = {} {} ))
                                AND       togther_card_answers.state IN (0)
                                AND       (
                                                    togther_card_answers.attachment_count = 0
                                          OR        togther_card_answers.attachments_uploaded = true )
                                GROUP BY  togther_collabcard.id) AS cs2
            ON        cs.card_id = cs2.card_id
            ORDER BY  {} limit {} offset {}; 
        """.format(community_id, excluded_card_types_tuple, pinned_chatrooms_query, user_id, excluded_card_id_string,
                   community_id, excluded_card_types_tuple, pinned_chatrooms_query, user_id, excluded_card_id_string,
                   order_by_query, limit, offset)

        curr.execute(sql)
        res = curr.fetchall()
        curr.close()

        ordered_card_ids = []
        for card_id in res:
            ordered_card_ids.append(card_id[0])

        return ordered_card_ids

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def check_user_has_member_can_initiate_dm_right(user_id, community_id, member_right_state):
    try:
        conn = get_connection()
        curr = conn.cursor()

        sql = """SELECT Count(*)
                FROM   togther_cohortmember
                WHERE  user_id = %s
                       AND cohort_id IN (SELECT cohort_id
                                         FROM   togther_cohortrights
                                         WHERE  cohort_id IN (SELECT id
                                                              FROM   togther_cohort
                                                              WHERE  community_id = %s)
                                                AND member_rights_id IN (SELECT id
                                                                         FROM
                                                    togther_memberrights
                                                                         WHERE  state = %s));
        """ % (str(user_id), str(community_id), str(member_right_state))
        curr.execute(sql)
        conversation_tuple = curr.fetchone()
        curr.close()

        if conversation_tuple:
            return conversation_tuple[0]

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_dm_chatrooms_of_user(user_id, community_id, custom_tag=''):
    try:
        conn = get_connection()
        curr = conn.cursor()

        if isinstance(community_id, list):
            community_id = "IN (" + ",".join([str(i) for i in community_id]) + ")"
        else:
            community_id = "=" + str(community_id)

        non_guest_user_query = get_user_ids_based_on_guest_filter(is_guest=False, only_sql_query=True)

        custom_tag_filter = ""
        if custom_tag:
            custom_tag_filter = f""" AND ccrd.custom_tag ILIKE '%{custom_tag.replace("'", "''")}%'"""

        sql = """
                SELECT cs.card_id,
                       cs.id
                FROM   togther_collabcardstate AS cs
                       INNER JOIN togther_collabcard AS ccrd
                               ON cs.card_id = CCRD.id
                       INNER JOIN togther_card_answers as ca
                               ON ca.card_id = ccrd.id
                WHERE  ccrd.community_id %s
                       AND cs.follow_status = TRUE
                       AND cs.remove_id IS NULL
                       AND cs.secret_chatroom_left = FALSE
                       AND cs.user_id = %s
                       AND ccrd.is_private = TRUE
                       AND ccrd.TYPE = 10
                       AND ca.state = 0
                       AND ( ccrd.user_id = %s
                              OR ccrd.chatroom_with_user_id = %s )
                       AND ( ccrd.user_id IN ( %s )
                             AND ccrd.chatroom_with_user_id IN ( %s ) ) 
                       %s
                       GROUP BY cs.card_id, cs.id;
        """ % (str(community_id), str(user_id), str(user_id), str(user_id), non_guest_user_query, non_guest_user_query,
               custom_tag_filter)

        curr.execute(sql)
        card_list = curr.fetchall()
        curr.close()

        return card_list

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_ordered_card_id_on_the_basis_newest_chatroom(user_id, community_id, is_pinned, excluded_card_ids,
                                                     excluded_card_types, page=1, limit=10):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        excluded_card_id_string = ""

        if excluded_card_ids:
            excluded_card_ids_tuple = get_tuple_from_array(excluded_card_ids)
            excluded_card_id_string = "AND CA.id NOT IN {}".format(excluded_card_ids_tuple)

        excluded_card_types_tuple = get_tuple_from_array(excluded_card_types)
        is_pinned = "true" if is_pinned else "false"

        conn = get_connection()
        curr = conn.cursor()

        sql = """SELECT CA.id
                    FROM   togther_collabcardstate AS CS
                           INNER JOIN togther_collabcard AS CA
                                   ON CS.card_id = CA.id
                    WHERE  ( CS.secret_chatroom_left = false
                             AND CA.community_id = {}
                             AND CA.is_pending = false
                             AND CA.is_deleted = false
                             AND CA.is_private = false
                             AND CA.type NOT IN {}
                             AND CA.is_pinned = {}
                             AND CS.user_id = {}
                             {} )
                    GROUP  BY CA.id
                    ORDER  BY CA.created_at DESC LIMIT {} OFFSET {} ;
        """.format(community_id, excluded_card_types_tuple, is_pinned, user_id, excluded_card_id_string, limit, offset)
        curr.execute(sql)
        res = curr.fetchall()
        curr.close()

        ordered_card_ids = []
        for card_id in res:
            ordered_card_ids.append(card_id[0])

        return ordered_card_ids
    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_ordered_card_id_on_the_basis_last_message(user_id, community_id, is_pinned, excluded_card_ids,
                                                  excluded_card_types, page=1, limit=10):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        excluded_card_id_string = ""

        if excluded_card_ids:
            excluded_card_ids_tuple = get_tuple_from_array(excluded_card_ids)
            excluded_card_id_string = "AND CA.id NOT IN {}".format(excluded_card_ids_tuple)

        excluded_card_types_tuple = get_tuple_from_array(excluded_card_types)
        is_pinned = "true" if is_pinned else "false"

        conn = get_connection()
        curr = conn.cursor()

        sql = """WITH added_row_number AS
                (
                         SELECT   ca.created_at,
                                  ca.id,
                                  ca.card_id,
                                  Row_number() OVER( partition BY ca.card_id ORDER BY ca.created_at DESC) AS row_number
                         FROM     togther_card_answers                                                    AS ca
                         WHERE    ca.card_id IN
                                  (
                                             SELECT     ca.id
                                             FROM       togther_collabcardstate AS cs
                                             INNER JOIN togther_collabcard      AS ca
                                             ON         cs.card_id = ca.id
                                             WHERE      (
                                                                   cs.secret_chatroom_left = false
                                                        AND        ca.community_id = {}
                                                        AND        ca.is_pending = false
                                                        AND        ca.is_deleted = false
                                                        AND        ca.is_private = false
                                                        AND        ca.type NOT IN {}
                                                        AND        ca.is_pinned = {}
                                                        AND        cs.user_id = {} {} )))
                SELECT   card_id
                FROM     added_row_number
                WHERE    row_number = 1
                ORDER BY created_at DESC limit {} offset {};
        """.format(community_id, excluded_card_types_tuple, is_pinned, user_id, excluded_card_id_string, limit, offset)
        curr.execute(sql)
        res = curr.fetchall()
        curr.close()

        ordered_card_ids = []
        for card_id in res:
            ordered_card_ids.append(card_id[0])

        return ordered_card_ids
    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_ordered_card_id_on_the_basis_of_participants_count(user_id, community_id, is_pinned, excluded_card_ids,
                                                           excluded_card_types, page=1, limit=10):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        excluded_card_id_string = ""

        if excluded_card_ids:
            excluded_card_ids_tuple = get_tuple_from_array(excluded_card_ids)
            excluded_card_id_string = "AND CA.id NOT IN {}".format(excluded_card_ids_tuple)

        excluded_card_types_tuple = get_tuple_from_array(excluded_card_types)
        is_pinned = "true" if is_pinned else "false"

        conn = get_connection()
        curr = conn.cursor()

        sql = """
            SELECT    togther_collabcard.id
            FROM      togther_collabcard
            LEFT JOIN togther_collabcardstate
            ON        togther_collabcard.id = togther_collabcardstate.card_id
            WHERE     togther_collabcard.id IN
                      (
                                 SELECT     ca.id
                                 FROM       togther_collabcardstate AS cs
                                 INNER JOIN togther_collabcard      AS ca
                                 ON         cs.card_id = ca.id
                                 WHERE      (
                                                       cs.secret_chatroom_left = false
                                            AND        ca.community_id = {}
                                            AND        ca.is_pending = false
                                            AND        ca.is_deleted = false
                                            AND        ca.is_private = false
                                            AND        ca.type NOT IN {}
                                            AND        ca.is_pinned = {}
                                            AND        cs.user_id = {} {} ))
            AND       togther_collabcardstate.follow_status = true
            AND       togther_collabcardstate.is_tagged = false
            AND       togther_collabcardstate.remove_id IS NULL
            GROUP BY  togther_collabcard.id
            ORDER BY  count(togther_collabcardstate.id) DESC limit {} offset {};
        """.format(community_id, excluded_card_types_tuple, is_pinned, user_id, excluded_card_id_string, limit, offset)

        curr.execute(sql)
        res = curr.fetchall()
        curr.close()

        ordered_card_ids = []
        for card_id in res:
            ordered_card_ids.append(card_id[0])

        return ordered_card_ids

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_ordered_card_id_on_the_basis_newest_chatroom_v2(user_id, community_id, is_pinned, excluded_card_ids,
                                                        excluded_card_types, pinned_chatrooms_list, page=1, limit=10,
                                                        chatroom_type=None):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        excluded_card_id_string = ""

        if excluded_card_ids:
            excluded_card_ids_tuple = get_tuple_from_array(excluded_card_ids)
            excluded_card_id_string = "AND CA.id NOT IN {}".format(excluded_card_ids_tuple)

        excluded_card_types_tuple = get_tuple_from_array(excluded_card_types)

        pinned_chatrooms_query = create_pinned_query_for_feed_revamp("AND CA.is_pinned = {}", is_pinned)

        order_by_query = "CA.created_at DESC"

        if (not is_pinned) and (len(pinned_chatrooms_list) <= MIN_NUMBER_OF_PIN_CHATROOMS_IN_FEED_REVAMP):
            order_by_query = "CA.is_pinned DESC, CA.created_at DESC"

        chatroom_type_filter = """ AND CA.type NOT IN (%s)""" % str(card_types.CARD_FEED_GROUP)

        if chatroom_type:
            chatroom_type_filter = """ AND CA.type IN (%s)""" % str(chatroom_type)

        conn = get_connection()
        curr = conn.cursor()

        sql = """SELECT CA.id
                    FROM   togther_collabcardstate AS CS
                           INNER JOIN togther_collabcard AS CA
                                   ON CS.card_id = CA.id
                    WHERE  ( CS.secret_chatroom_left = false
                             AND CA.community_id = {}
                             AND CA.is_pending = false
                             AND CA.is_deleted = false
                             AND CA.is_private = false
                             AND CA.type NOT IN {}
                             {}
                             AND CS.user_id = {}
                             {} {})
                    GROUP  BY CA.id
                    ORDER  BY {} LIMIT {} OFFSET {} ;
        """.format(community_id, excluded_card_types_tuple, pinned_chatrooms_query, user_id, excluded_card_id_string,
                   chatroom_type_filter, order_by_query, limit, offset)

        curr.execute(sql)
        res = curr.fetchall()
        curr.close()

        ordered_card_ids = []
        for card_id in res:
            ordered_card_ids.append(card_id[0])

        return ordered_card_ids
    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_ordered_card_id_on_the_basis_last_message_v2(user_id, community_id, is_pinned, excluded_card_ids,
                                                     excluded_card_types, pinned_chatrooms_list, page=1, limit=10):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        excluded_card_id_string = ""

        if excluded_card_ids:
            excluded_card_ids_tuple = get_tuple_from_array(excluded_card_ids)
            excluded_card_id_string = "AND CA.id NOT IN {}".format(excluded_card_ids_tuple)

        excluded_card_types.append(card_types.CARD_FEED_GROUP)
        excluded_card_types_tuple = get_tuple_from_array(excluded_card_types)

        pinned_chatrooms_query = create_pinned_query_for_feed_revamp("AND ca.is_pinned = {}", is_pinned)

        order_by_query = "added_row_number.created_at DESC"

        if (not is_pinned) and (len(pinned_chatrooms_list) <= MIN_NUMBER_OF_PIN_CHATROOMS_IN_FEED_REVAMP):
            order_by_query = "togther_collabcard.is_pinned DESC, added_row_number.created_at DESC"

        conn = get_connection()
        curr = conn.cursor()

        sql = """
                WITH added_row_number AS
                (
                         SELECT   ca.created_at,
                                  ca.id,
                                  ca.card_id,
                                  Row_number() OVER( partition BY ca.card_id ORDER BY ca.created_at DESC) AS row_number
                         FROM     togther_card_answers                                                    AS ca
                         WHERE    ca.card_id IN
                                  (
                                             SELECT     ca.id
                                             FROM       togther_collabcardstate AS cs
                                             INNER JOIN togther_collabcard      AS ca
                                             ON         cs.card_id = ca.id
                                             WHERE      (
                                                                   cs.secret_chatroom_left = false
                                                        AND        ca.community_id = {}
                                                        AND        ca.is_pending = false
                                                        AND        ca.is_deleted = false
                                                        AND        ca.is_private = false
                                                        AND        ca.type NOT IN {}
                                                        {}
                                                        AND        cs.user_id = {} {} )))
                SELECT     togther_collabcard.id
                FROM       togther_collabcard
                INNER JOIN added_row_number
                ON         added_row_number.card_id=togther_collabcard.id
                WHERE    added_row_number.row_number = 1
                ORDER BY {} limit {} offset {};
        """.format(community_id, excluded_card_types_tuple, pinned_chatrooms_query, user_id, excluded_card_id_string,
                   order_by_query, limit, offset)
        curr.execute(sql)
        res = curr.fetchall()
        curr.close()

        ordered_card_ids = []
        for card_id in res:
            ordered_card_ids.append(card_id[0])

        return ordered_card_ids
    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_ordered_card_id_on_the_basis_of_participants_count_v2(user_id, community_id, is_pinned, excluded_card_ids,
                                                              excluded_card_types, pinned_chatrooms_list, page=1,
                                                              limit=10, chatroom_type=None):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        excluded_card_id_string = ""

        if excluded_card_ids:
            excluded_card_ids_tuple = get_tuple_from_array(excluded_card_ids)
            excluded_card_id_string = "AND CA.id NOT IN {}".format(excluded_card_ids_tuple)

        excluded_card_types_tuple = get_tuple_from_array(excluded_card_types)
        pinned_chatrooms_query = create_pinned_query_for_feed_revamp("AND ca.is_pinned = {}", is_pinned)

        order_by_query = "count(togther_collabcardstate.id) DESC"

        if (not is_pinned) and (len(pinned_chatrooms_list) <= MIN_NUMBER_OF_PIN_CHATROOMS_IN_FEED_REVAMP):
            order_by_query = "togther_collabcard.is_pinned DESC, count(togther_collabcardstate.id) DESC"

        chatroom_type_filter = """ AND CA.type NOT IN (%s)""" % str(card_types.CARD_FEED_GROUP)

        if chatroom_type:
            chatroom_type_filter = """ AND CA.type IN (%s)""" % str(chatroom_type)

        conn = get_connection()
        curr = conn.cursor()

        sql = """
            SELECT    togther_collabcard.id
            FROM      togther_collabcard
            LEFT JOIN togther_collabcardstate
            ON        togther_collabcard.id = togther_collabcardstate.card_id
            WHERE     togther_collabcard.id IN
                      (
                                 SELECT     ca.id
                                 FROM       togther_collabcardstate AS cs
                                 INNER JOIN togther_collabcard      AS ca
                                 ON         cs.card_id = ca.id
                                 WHERE      (
                                                       cs.secret_chatroom_left = false
                                            AND        ca.community_id = {}
                                            AND        ca.is_pending = false
                                            AND        ca.is_deleted = false
                                            AND        ca.is_private = false
                                            AND        ca.type NOT IN {}
                                            {}
                                            {}
                                            AND        cs.user_id = {} {} ))
            AND       togther_collabcardstate.user_id IN 
                      (
                         SELECT user_id_id
                         FROM   togther_userinfo
                         WHERE  is_guest = false )
            AND       togther_collabcardstate.follow_status = true
            AND       togther_collabcardstate.is_tagged = false
            AND       togther_collabcardstate.remove_id IS NULL
            GROUP BY  togther_collabcard.id
            ORDER BY  {} limit {} offset {};
        """.format(community_id, excluded_card_types_tuple, pinned_chatrooms_query, chatroom_type_filter, user_id,
                   excluded_card_id_string, order_by_query, limit, offset)

        curr.execute(sql)
        res = curr.fetchall()
        curr.close()

        ordered_card_ids = []
        for card_id in res:
            ordered_card_ids.append(card_id[0])

        return ordered_card_ids

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_last_conversation_id_corresponding_to_chatrooms_list(chatrooms_list, excluded_conversation_state=[], page=1,
                                                             limit=10):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        card_tuple = get_tuple_from_array(chatrooms_list)
        excluded_conv_states = get_tuple_from_array(excluded_conversation_state)

        conn = get_connection()
        curr = conn.cursor()

        sql = """WITH added_row_number AS
                (
                         SELECT   ca.created_at,
                                  ca.id,
                                  ca.card_id,
                                  ca.state,
                                  row_number() OVER( partition BY ca.card_id ORDER BY (
                                  CASE
                                           WHEN ca.state NOT IN %s THEN 1
                                           ELSE 2
                                  END), ca.created_at DESC) AS row_number
                         FROM     togther_card_answers      AS ca
                         WHERE    ca.card_id IN %s
                         AND NOT  (
                                    ca.attachment_count > 0 
                                    AND ca.attachments_uploaded = false
                                  )   
                )
                SELECT   card_id,
                         id,
                         created_at
                FROM     added_row_number
                WHERE    row_number = 1 and state NOT IN %s
                ORDER BY created_at DESC limit %s offset %s; 
        """ % (excluded_conv_states, card_tuple, excluded_conv_states,  str(limit), str(offset))
        curr.execute(sql)
        card_list = curr.fetchall()
        curr.close()

        return {data[0]: data[1] for data in card_list}

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_conversations_after_last_seen_messages_in_chatrooms(chatrooms_list, data_state=0):
    try:
        if not (chatrooms_list or data_state):
            return 0

        chatrooms_list_string = ",".join([str(card_id) for card_id in chatrooms_list])

        included_conv_states = [conversation_states.ANSWER, conversation_states.CONVERSATION_HEADER,
                                conversation_states.CONVERSATION_POLL]

        included_conv_states_query = get_tuple_from_array(included_conv_states)

        raw_data = "CS.card_id, CA.id, CA.state"
        additional_filter = ""

        if not data_state:
            raw_data = "Count(*)"
            additional_filter = "AND CA.state IN {}".format(included_conv_states_query)

        conn = get_connection()
        curr = conn.cursor()

        sql = """SELECT %s
                FROM   togther_card_answers AS CA
                       INNER JOIN togther_collabcardstate AS CS
                               ON CA.card_id = CS.card_id
                WHERE  CS.id IN (%s)
                       AND ( ( CS.last_seen_conversation_id IS NOT NULL
                               AND CA.id > CS.last_seen_conversation_id )
                              OR ( CS.last_seen_conversation_id IS NULL ) ) %s; 
        """ % (raw_data, chatrooms_list_string, additional_filter)

        curr.execute(sql)
        data = curr.fetchall()
        curr.close()

        if not data_state:
            return data[0][0]

        return data

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_participant_counts_on_basis_of_chatroom_ids(card_ids_list):
    try:
        card_tuple = ",".join([str(card_id) for card_id in card_ids_list])

        conn = get_connection()
        curr = conn.cursor()

        sql = """SELECT card_id,
                        Count(*)
                 FROM  togther_collabcardstate
                 WHERE card_id IN (%s)
                       AND follow_status = true
                       AND is_tagged = false
                       AND remove_id IS NULL
                 GROUP BY card_id;""" % card_tuple
        curr.execute(sql)
        card_list = curr.fetchall()
        curr.close()

        return {data[0]: data[1] for data in card_list}

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_all_chatrooms_of_community(community_id, chatroom_filter_type, chatroom_excluded_type, page=1, limit=10):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        excluded_type_list = [10]
        if chatroom_excluded_type:
            excluded_type_list.extend(chatroom_excluded_type)

        excluded_type_list = ",".join([str(i) for i in excluded_type_list])
        filter_type_list = ",".join([str(i) for i in chatroom_filter_type])

        type_exclude_filter = """AND togther_collabcard.type NOT IN (%s)""" % excluded_type_list if \
            excluded_type_list else ""
        type_include_filter = """AND togther_collabcard.type IN (%s)""" % filter_type_list if filter_type_list else ""

        get_creator_data = ",".join([get_users_query_meta_for_sync_revamp("creator"),
                                     get_members_query_meta_for_sync_revamp("creator"),
                                     get_sdk_client_query_meta_for_sync_revamp("creator")])

        conn = get_connection()
        curr = conn.cursor()

        sql = """SELECT chatrooms_data.*, %s FROM
                 (SELECT %s, COUNT(*) as participants_count, 
                 TO_CHAR(to_timestamp(togther_collabcard.created_at / 1000), 'DD Mon YYYY') AS date
                 FROM  togther_collabcard
                 INNER JOIN togther_collabcardstate
                 ON togther_collabcard.id = togther_collabcardstate.card_id
                 INNER JOIN togther_userinfo
                 ON togther_userinfo.user_id_id = togther_collabcardstate.user_id
                 WHERE (togther_collabcard.is_deleted = false
                       AND togther_collabcard.is_private = false
                       AND togther_collabcard.community_id = %s 
                       AND "togther_collabcardstate"."follow_status" = true
                       AND "togther_collabcardstate"."is_tagged" = false
                       AND "togther_collabcardstate"."remove_id" is NULL
                       AND togther_userinfo.is_guest = false %s %s)
                       GROUP BY togther_collabcard.id
                       ORDER BY togther_collabcard.created_at DESC
                       limit %s offset %s) AS chatrooms_data
                 
                LEFT JOIN togther_userinfo ON (
                  togther_userinfo.user_id_id = chatrooms_data.user_id
                ) 
                LEFT JOIN togther_members ON (
                  chatrooms_data.user_id = togther_members.member_id_id 
                  AND chatrooms_data.community_id = togther_members.community_id_id
                )
                LEFT JOIN togther_sdkclientusersinfo ON (
                    chatrooms_data.user_id = togther_sdkclientusersinfo.user_id
                );""" % \
              (get_creator_data, get_chatroom_query_meta_for_sync_revamp(), str(community_id), type_exclude_filter,
               type_include_filter, limit, offset)

        curr.execute(sql)
        chatroom_data = convert_sql_query_result_to_dict(curr, curr.fetchall())
        curr.close()

        return chatroom_data

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_all_chatrooms_of_community_old(community_id, chatroom_filter_type, chatroom_excluded_type):
    try:

        excluded_type_list = [10]
        if chatroom_excluded_type:
            excluded_type_list.extend(chatroom_excluded_type)

        excluded_type_list = ",".join([str(i) for i in excluded_type_list])
        filter_type_list = ",".join([str(i) for i in chatroom_filter_type])

        type_exclude_filter = """AND type NOT IN (%s)""" % excluded_type_list if excluded_type_list else ""
        type_include_filter = """AND type IN (%s)""" % filter_type_list if filter_type_list else ""

        conn = get_connection()
        curr = conn.cursor()

        sql = """SELECT id
                 FROM  togther_collabcard
                 WHERE (is_deleted = false
                       AND is_private = false
                       AND community_id = %s 
                       %s
                       %s);""" % (str(community_id), type_exclude_filter, type_include_filter)

        curr.execute(sql)
        card_list = curr.fetchall()
        curr.close()

        return [data[0] for data in card_list]

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def fetch_user_communities_sorted_by_order_time(user_id, community_id=None):
    try:
        conn = get_connection()
        curr = conn.cursor()

        community_id_query = ""

        if community_id:
            community_id_query = "AND community_id_id = {}".format(community_id)

        sql = """
                SELECT   id
                FROM     togther_member_engage
                WHERE    (member_id_id = %s %s)
                ORDER BY order_time DESC;""" % (str(user_id), community_id_query)

        curr.execute(sql)
        card_list = curr.fetchall()
        curr.close()

        return [data[0] for data in card_list]

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_user_ids_based_on_guest_filter(is_guest=False, only_sql_query=False):
    try:
        sql = """
                SELECT   user_id_id
                FROM     togther_userinfo
                WHERE    is_guest = %s""" % is_guest

        if only_sql_query:
            return sql

        conn = get_connection()
        curr = conn.cursor()

        curr.execute(sql)
        user_list = curr.fetchall()
        curr.close()

        return [data[0] for data in user_list]

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_chatroom_participants_count(chatroom_id, community_id):
    """Returns the participants count of chatroom in community"""

    try:
        
        current_time = TimeUtilities.current_time_in_milliseconds()

        error_logger.error(f"[raw_query] Starting get_chatroom_participants_count for chatroom_id {chatroom_id} and community_id {community_id} ")

        conn = get_connection()
        curr = conn.cursor()

        sql = """SELECT COUNT(DISTINCT("togther_members"."member_id_id"))
                FROM "togther_members"
                INNER JOIN "togther_collabcardstate"
                    ON ("togther_members"."member_id_id" = "togther_collabcardstate"."user_id")
                WHERE ("togther_members"."community_id_id" = %s
                        AND "togther_collabcardstate"."follow_status" = true
                        AND "togther_collabcardstate"."card_id" = %s
                        AND "togther_collabcardstate"."is_tagged" = false
                        AND "togther_collabcardstate"."remove_id" is NULL 
                        AND "togther_collabcardstate"."user_id" IN 
                        (
                            SELECT user_id_id FROM togther_userinfo WHERE is_guest = false
                        ));""" % (str(community_id), str(chatroom_id))

        curr.execute(sql)
        participants_count = curr.fetchone()
        curr.close()

        end_time = TimeUtilities.current_time_in_milliseconds()

        error_logger.error(f"[raw_query] ({current_time - end_time} ms) Done get_chatroom_participants_count for chatroom_id {chatroom_id} and community_id {community_id} ")

        if participants_count:
            return participants_count[0]

        return 0

    except (Exception, psycopg2.Error) as error:
        print(error)
        error_logger.error("Error while connecting to PostgreSQL %s ", error)

        return 0


def get_sorted_user_data_on_basis_of_activity_in_chatroom(chatroom_id, user_id=None, page=1, limit=50,
                                                          follow_status=True, is_guest=False, filter_user_ids=None):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        conn = get_connection()
        curr = conn.cursor()

        filter_user_query = ""

        if filter_user_ids is not None:
            filter_user_query = " AND togther_collabcardstate.user_id IN {}".format(
                get_tuple_from_array(filter_user_ids))

        sql = """
                SELECT     user_id_id AS id,
                           NAME,
                           image_link AS image_url,
                           is_guest,
                           togther_userinfo.user_unique_id,
                           togther_userinfo.user_unique_id           AS uuid,
                           togther_sdkclientusersinfo.user_unique_id AS sdk_client_info___user_unique_id,
                           togther_sdkclientusersinfo.user_unique_id AS sdk_client_info___uuid,
                           togther_sdkclientusersinfo.community_id   AS sdk_client_info___community,
                           togther_sdkclientusersinfo.user_id        AS sdk_client_info___user,
                           togther_sdkclientusersinfo.widget_id      AS sdk_client_info___widget_id 

                FROM       togther_userinfo
                INNER JOIN
                           (
                                      SELECT     ans_ord.user_id
                                      FROM       togther_userinfo AS usrinfo
                                      INNER JOIN
                                                 (
                                                           SELECT    togther_collabcardstate.user_id,
                                                                     COALESCE(Max(togther_card_answers.created_at), 0) AS created_at
                                                           FROM      togther_collabcardstate
                                                           LEFT JOIN togther_card_answers
                                                           ON        togther_card_answers.user_id = togther_collabcardstate.user_id
                                                           WHERE     togther_collabcardstate.card_id = {}
                                                           AND       togther_collabcardstate.follow_status = {}
                                                           AND       togther_collabcardstate.remove_id IS NULL
                                                           AND       togther_collabcardstate.is_tagged = false {}
                                                           GROUP BY  togther_card_answers.user_id,
                                                                     togther_collabcardstate.user_id
                                                           ORDER BY  max(
                                                                     CASE
                                                                               WHEN togther_card_answers.created_at IS NULL THEN 0
                                                                               ELSE togther_card_answers.created_at
                                                                     END) DESC) AS ans_ord
                                      ON         ans_ord.user_id = usrinfo.user_id_id
                                      WHERE      (usrinfo.is_guest = {}
                                                  AND usrinfo.user_id_id != {})
                                      GROUP BY   ans_ord.user_id
                                      ORDER BY   max(ans_ord.created_at) DESC limit {} offset {}) AS ordered_data
                ON         ordered_data.user_id=togther_userinfo.user_id_id
                LEFT JOIN togther_sdkclientusersinfo 
                ON togther_sdkclientusersinfo.user_id = togther_userinfo.user_id_id;
        """.format(chatroom_id, follow_status, filter_user_query, is_guest, user_id, limit, offset)

        curr.execute(sql)
        user_ids_list = curr.fetchall()
        columns = [col[0] for col in curr.description]
        curr.close()

        users_data = [dict(zip(columns, row)) for row in user_ids_list]

        # Process users data to add sdk client info
        users_meta = process_users_meta_data_from_query_response(users_data, list_only=True)

        return users_meta

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_community_members_data_on_basis_of_name_search(community_id, chatroom_id, user_id=None, page=1, limit=50,
                                                       is_guest=False, member_name_search: str = None,
                                                       filter_user_ids: list = None,
                                                       tag_only_participants: bool = False):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        conn = get_connection()
        curr = conn.cursor()

        filter_user_query = ""
        tag_only_participants_user_query = ""

        if filter_user_ids is not None:
            filter_user_query = """ 
                INNER JOIN togther_collabcardstate 
                ON (togther_collabcardstate.user_id = togther_userinfo.user_id_id AND
                    togther_collabcardstate.user_id IN {} AND
                    togther_collabcardstate.follow_status = true AND
                    togther_collabcardstate.card_id = {})
            """.format(get_tuple_from_array(filter_user_ids), chatroom_id)

        if tag_only_participants:
            tag_only_participants_user_query = """ 
                INNER JOIN togther_collabcardstate 
                ON (togther_collabcardstate.user_id = togther_userinfo.user_id_id AND
                    togther_collabcardstate.follow_status = true AND
                    togther_collabcardstate.card_id = {})
            """.format(chatroom_id)

        sql = """
                SELECT     togther_userinfo.user_id_id AS id,
                           togther_userinfo.NAME,
                           (CASE
                                WHEN togther_members.image_url IS NOT NULL THEN togther_members.image_url
                                WHEN togther_userinfo.image_link IS NOT NULL THEN togther_userinfo.image_link
                                ELSE ''
                            END) AS image_url,
                           togther_userinfo.is_guest,
                           togther_userinfo.user_unique_id,
                           togther_userinfo.user_unique_id as uuid,
                           togther_sdkclientusersinfo.user_unique_id    AS sdk_client_info___user_unique_id,
                           togther_sdkclientusersinfo.user_unique_id    AS sdk_client_info___uuid,
                           togther_sdkclientusersinfo.community_id      AS sdk_client_info___community, 
                           togther_sdkclientusersinfo.user_id           AS sdk_client_info___user,
                           togther_sdkclientusersinfo.widget_id         AS sdk_client_info___widget_id 
                FROM       togther_userinfo
                INNER JOIN togther_members
                ON         togther_members.member_id_id=togther_userinfo.user_id_id {} {}
                AND        togther_members.community_id_id={}
                AND        togther_userinfo.is_guest={}
                AND        togther_userinfo.user_id_id!={}
                LEFT JOIN  togther_sdkclientusersinfo 
                ON         togther_sdkclientusersinfo.user_id = togther_userinfo.user_id_id
                WHERE      togther_userinfo.NAME ILIKE '{}%'
                ORDER BY   togther_userinfo.NAME ASC limit {} offset {};
        """.format(filter_user_query, tag_only_participants_user_query, community_id, is_guest, user_id,
                   member_name_search, limit, offset)

        curr.execute(sql)
        user_ids_list = curr.fetchall()
        columns = [col[0] for col in curr.description]
        curr.close()

        users_data = [dict(zip(columns, row)) for row in user_ids_list]

        # process users data to add sdk client info
        users_meta = process_users_meta_data_from_query_response(users_data, list_only=True)

        return users_meta

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_conversation_users_against_chatrooms_list(chatroom_ids_list, number_of_conversation_users: int = 2):
    try:
        conn = get_connection()
        curr = conn.cursor()

        sql = """
            SELECT ans_query.community_id,
                   ans_query.card_id,
                   togther_userinfo.user_id_id,
                   togther_userinfo.name,
                   togther_userinfo.image_link,
                   togther_members.id,
                   togther_members.image_url
            FROM   togther_userinfo
                   INNER JOIN (WITH added_row_number
                                    AS (SELECT togther_card_answers.card_id,
                                               togther_card_answers.user_id,
                                               togther_card_answers.community_id,
                                               Row_number()
                                                 over(
                                                   PARTITION BY togther_card_answers.card_id
                                                   ORDER BY
                                                 Max(togther_card_answers.created_at)
                                                 DESC) AS
                                               row_number
                                        FROM   togther_card_answers
                                               inner join togther_collabcard
                                                       ON togther_collabcard.id =
                                                          togther_card_answers.card_id
                                        WHERE  togther_card_answers.card_id IN %s
                                               AND togther_card_answers.state = 0
                                               AND togther_collabcard.user_id !=
                                                   togther_card_answers.user_id
                                        GROUP  BY togther_card_answers.community_id,
                                                  togther_card_answers.card_id,
                                                  togther_card_answers.user_id
                                        ORDER  BY Max(togther_card_answers.created_at) DESC)
                               SELECT community_id,
                                      card_id,
                                      user_id,
                                      row_number
                                FROM   added_row_number
                                WHERE  row_number < %s) AS ans_query
                           ON togther_userinfo.user_id_id = ans_query.user_id
                   LEFT JOIN togther_members
                          ON ans_query.user_id = togther_members.member_id_id
                             AND ans_query.community_id = togther_members.community_id_id;
        """ % (get_tuple_from_array(chatroom_ids_list), number_of_conversation_users + 1)

        curr.execute(sql)
        conversation_users_data = curr.fetchall()
        curr.close()

        conversation_user_dict = {}

        for chatroom_conversation_data in conversation_users_data:
            user_data = {
                "id": chatroom_conversation_data[2],
                "name": chatroom_conversation_data[3]
            }

            if not chatroom_conversation_data[5]:
                user_data["image_url"] = REMOVED_USER_URL

            elif chatroom_conversation_data[6]:
                user_data["image_url"] = chatroom_conversation_data[6]

            else:
                user_data["image_url"] = chatroom_conversation_data[4]

            if not conversation_user_dict.get(chatroom_conversation_data[1]):
                conversation_user_dict[chatroom_conversation_data[1]] = [user_data]

            else:
                conversation_user_dict.get(chatroom_conversation_data[1]).append(user_data)

        return conversation_user_dict

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)

        return {}


def get_latest_conversations_against_chatrooms_list(chatroom_ids_list, number_of_conversations_per_chatroom: int = 2):
    try:
        conn = get_connection()
        curr = conn.cursor()


        included_conv_states = [conversation_states.ANSWER, conversation_states.CONVERSATION_HEADER,
                                conversation_states.CONVERSATION_POLL]

        included_conv_states_query = get_tuple_from_array(included_conv_states)

        sql = """
                WITH added_row_number
                     AS (SELECT togther_card_answers.card_id,
                                togther_card_answers.id AS ans_id,
                                togther_card_answers.user_id,
                                Row_number()
                                  OVER(
                                    partition BY togther_card_answers.card_id
                                    ORDER BY togther_card_answers.created_at DESC) AS row_number
                         FROM   togther_card_answers
                         WHERE  togther_card_answers.card_id IN %s
                                AND togther_card_answers.state IN %s
                                AND NOT ( 
                                            togther_card_answers.attachment_count > 0
                                            AND togther_card_answers.attachments_uploaded = False
                                        )
                         ORDER  BY togther_card_answers.created_at DESC)
                SELECT card_id,
                       ans_id,
                       user_id,
                       row_number
                FROM   added_row_number
                WHERE  row_number < %s;
        """ % (get_tuple_from_array(chatroom_ids_list), included_conv_states_query, 
               number_of_conversations_per_chatroom + 1)

        curr.execute(sql)
        chatroom_conversations_data = curr.fetchall()
        curr.close()

        chatroom_conversation_dict = {}

        for chatroom_conversation_data in chatroom_conversations_data:

            if not chatroom_conversation_dict.get(chatroom_conversation_data[0]):
                chatroom_conversation_dict[chatroom_conversation_data[0]] = [chatroom_conversation_data[1]]

            else:
                chatroom_conversation_dict.get(chatroom_conversation_data[0]).append(chatroom_conversation_data[1])

        return chatroom_conversation_dict

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)

        return {}


def activate_chatroom_for_followed_users_on_conversation_creation(card_id, user_id):
    """function to set active time after new conversation created"""

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = """
                UPDATE togther_collabcardstate
                SET    updated_at=%s
                WHERE  card_id=%s
                AND    follow_status=true
                AND    remove_id IS NULL
                AND    user_id!=%s;""" % (str(TimeUtilities.current_time_in_sec()), str(card_id), str(user_id))

        curr.execute(sql)
        conn.commit()

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_chatroom_query_meta_for_sync_revamp(key_name_prefix: str = None):
    query_fields = ['id', 'title', 'community_id', 'type', 'date_time', 'is_pending',
                    'date_epoch', 'share_link', 'user_id', 'has_been_named', 'header', 'access_without_subscription',
                    'has_files', 'about', 'co_hosts', 'online_link', 'og_tags', 'internal_link',
                    'deleted_by_user_id', 'attachment_count', 'attachments_uploaded', 'is_secret',
                    'secret_chatroom_participants', 'has_reactions', 'device_id', 'topic_id', 'auto_follow_done',
                    'is_edited', 'is_paid', 'access', 'is_private', 'chatroom_with_user_id', 'member_can_message',
                    'online_link_type', 'is_private_member', 'chatroom_image_url', 'created_at', 'custom_tag',
                    'updated_at', 'event_kind']

    meta_query = create_query_with_prefix(query_fields, 'togther_collabcard', 'chatroom', key_name_prefix)

    return ",".join(meta_query)


def get_chatroom_state_query_meta_for_sync_revamp(key_name_prefix: str = None):
    query_fields = ['state', 'mute_status', 'follow_status', 'is_tagged', 'last_seen_conversation_id',
                    'expiry_time', 'attending_status', 'secret_chatroom_left', 'external_seen',
                    'chat_request_state', 'chat_requested_by_id', 'chat_request_created_at', 'card_id']

    meta_query = create_query_with_prefix(query_fields, 'togther_collabcardState', 'chatroom_state', key_name_prefix)

    return ",".join(meta_query)


def create_query_with_prefix(query_fields, table_name, key_name_prefix: str = None, key_name_suffix: str = None):
    if key_name_suffix:
        meta_query = ["".join([table_name, '.', query_field, " AS {}___{}___{}".format(
            key_name_prefix, query_field, key_name_suffix)]) for query_field in query_fields]

    elif key_name_suffix is not None:
        meta_query = ["".join([table_name, '.', query_field, " AS {}___{}".format(key_name_prefix, query_field)])
                      for query_field in query_fields]

    else:
        meta_query = ["".join([table_name, '.', query_field]) for query_field in query_fields]

    return meta_query


def get_conversation_query_meta_for_sync_revamp(key_name_prefix: str = None):
    query_fields = ['id', 'answer', 'created_at', 'state', 'is_edited', 'has_files', 'attachment_count',
                    'attachments_uploaded', 'card_id', 'user_id', 'community_id', 'og_tags', 'deleted_by_user_id',
                    'internal_link', 'reply_id', 'last_updated', 'preview_chatroom_id', 'preview_type', 'api_version',
                    'temporary_id', 'poll_type', 'multiple_select_state', 'multiple_select_no', 'is_anonymous',
                    'allow_add_option', 'expiry_time', 'preview_community_id', 'has_reactions', 'device_id',
                    'poll_answer_text', 'reply_chatroom_id', 'header', 'location', 'location_lat', 'location_long',
                    'start_time', 'end_time', 'online_link_enable_before', 'co_hosts']

    meta_query = create_query_with_prefix(query_fields, 'togther_card_answers', 'conversation', key_name_prefix)

    return ",".join(meta_query)


def get_community_query_meta_for_sync_revamp(key_name_prefix: str = None):
    query_fields = ['id', 'name', 'purpose', 'image_url', 'type', 'sub_type', 'is_paid']
    meta_query = create_query_with_prefix(query_fields, 'togther_community', 'community', key_name_prefix)

    return ",".join(meta_query)


def get_members_query_meta_for_sync_revamp(key_name_prefix: str = None):
    query_fields = ['member_id_id', 'state', 'image_url', 'is_owner', 'custom_title', 'created_at']
    meta_query = create_query_with_prefix(query_fields, 'togther_members', 'member', key_name_prefix)

    return ",".join(meta_query)

def get_users_query_meta_for_sync_revamp(key_name_prefix: str = None):
    query_fields = ['user_id_id', 'name', 'image_link', 'user_unique_id', 'is_guest']
    meta_query = create_query_with_prefix(query_fields, 'togther_userinfo', 'user', key_name_prefix)

    # To add uuid in user object
    userinfo_uuid = f'togther_userinfo.user_unique_id AS user___uuid___{key_name_prefix}'

    return ",".join(meta_query + [userinfo_uuid])

def get_sdk_client_query_meta_for_sync_revamp(key_name_prefix: str = None):
    query_fields = ['user_unique_id', 'community_id', 'widget_id']
    meta_query = create_query_with_prefix(query_fields, 'togther_sdkclientusersinfo', 'sdk_client_info', key_name_prefix)

    # To add uuid and user in sdk_client_info object
    userinfo_uuid = f'togther_sdkclientusersinfo.user_unique_id AS sdk_client_info___uuid___{key_name_prefix}'
    userinfo_id = f'togther_sdkclientusersinfo.user_id AS sdk_client_info___id___{key_name_prefix}'
    userinfo_user = f'togther_sdkclientusersinfo.user_id AS sdk_client_info___user___{key_name_prefix}'

    return ",".join(meta_query + [userinfo_uuid, userinfo_id, userinfo_user])


def get_reactions_query_meta_for_sync_revamp(key_name_prefix: str = None):
    query_fields = ['id', 'reaction', 'chatroom_id', 'conversation_id', 'user_id']

    meta_query = create_query_with_prefix(query_fields, 'togther_MessageReactions', 'message_reactions',
                                          key_name_prefix)

    return ",".join(meta_query)


def get_card_attachments_query_meta_for_sync_revamp(key_name_prefix: str = None):
    query_fields = ['id', 'attachment', 'type', 'collabcard_id', 'file_url', 'index', 'dimensions', 'height', 'width',
                    'thumbnail_url', 'meta', 'name']

    meta_query = create_query_with_prefix(query_fields, 'togther_Card_Attachment', 'card_attachment',
                                          key_name_prefix)

    return ",".join(meta_query)


def get_conversation_attachments_query_meta_for_sync_revamp(key_name_prefix: str = None):
    query_fields = ['id', 'type', 'answer_id', 'file_url', 'index', 'dimensions', 'height', 'width',
                    'thumbnail_url', 'meta', 'name', 'created_at', 'location_lat', 'location_long', 'location_name']

    meta_query = create_query_with_prefix(query_fields, 'togther_answerAttachment', 'conv_attachment',
                                          key_name_prefix)

    return ",".join(meta_query)


def get_conversation_polls_query_meta_for_sync_revamp(key_name_prefix: str = None):
    query_fields = ['id', 'text', 'created_at', 'updated_at', 'conversation_id', 'user_id']

    meta_query = create_query_with_prefix(query_fields, 'togther_conversationPolls', 'conv_polls',
                                          key_name_prefix)

    return ",".join(meta_query)


def get_conversation_poll_members_query_meta_for_sync_revamp(key_name_prefix: str = None):
    query_fields = ['id', 'poll_id', 'created_at', 'conversation_id', 'user_id']

    meta_query = create_query_with_prefix(query_fields, 'togther_conversationPollMembers', 'conv_poll_members',
                                          key_name_prefix)

    return ",".join(meta_query)


def get_query_fields_for_members_meta(key_name_prefix: str = None):

    members_query = ['custom_title']
    members_meta_query = create_query_with_prefix(members_query, 'togther_members', 'member', key_name_prefix)
  
    user_info_fields = ['name', 'user_unique_id', 'is_guest']
    user_meta_query = create_query_with_prefix(user_info_fields, 'togther_userinfo', 'user', key_name_prefix)

    return ",".join(members_meta_query + user_meta_query)


def convert_sql_query_result_to_dict(cursor, result):
    """Return all rows from a cursor as a dict"""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in result]


def get_home_feed_chatrooms_against_user(user_id, community_id, min_timestamp: int = None, max_timestamp: int = None,
                                         page: int = 1, limit: int = 10, included_chatroom_types: list = None,
                                         only_query: bool = False):

    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        min_timestamp = TimeUtilities.convert_sec_to_milliseconds(int(min_timestamp))
        max_timestamp = TimeUtilities.convert_sec_to_milliseconds(int(max_timestamp))

        is_dm_chatroom = card_types.CARD_DIRECT_MESSAGE in included_chatroom_types

        included_chatroom_types_query = get_tuple_from_array(included_chatroom_types)

        chatroom_query = ",".join([get_chatroom_query_meta_for_sync_revamp(),
                                   get_chatroom_state_query_meta_for_sync_revamp()])

        creator_data_query = ",".join([get_users_query_meta_for_sync_revamp("creator"),
                                       get_members_query_meta_for_sync_revamp("creator"),
                                       get_sdk_client_query_meta_for_sync_revamp("creator")])

        chatroom_with_user_data_query = ",".join([get_users_query_meta_for_sync_revamp("dm_user"),
                                                  get_members_query_meta_for_sync_revamp("dm_user"),
                                                  get_sdk_client_query_meta_for_sync_revamp("dm_user")])

        chat_requested_user_data_query = ",".join([get_users_query_meta_for_sync_revamp("chat_requested"),
                                                   get_members_query_meta_for_sync_revamp("chat_requested"),
                                                   get_sdk_client_query_meta_for_sync_revamp("chat_requested")])

        topic_conversation_data_query = ",".join([get_users_query_meta_for_sync_revamp("last_conv"),
                                                  get_members_query_meta_for_sync_revamp("last_conv"),
                                                  get_sdk_client_query_meta_for_sync_revamp("last_conv"),
                                                  get_conversation_query_meta_for_sync_revamp("topic")])

        topic_user_data_query = ",".join([get_users_query_meta_for_sync_revamp("topic"),
                                          get_members_query_meta_for_sync_revamp("topic"),
                                          get_sdk_client_query_meta_for_sync_revamp("topic")])

        dm_chatroom_conversation_query = ""
        dm_chatroom_message_query = ""
        dm_chatroom_message_filter_query = ""

        if is_dm_chatroom:
            dm_chatroom_conversation_query = """LEFT JOIN togther_card_answers ON 
            togther_card_answers.card_id = togther_collabcard.id"""

            dm_chatroom_message_query = """
            ,(
                CASE
                    WHEN togther_collabcard.type = 10 AND togther_collabcard.is_private = true AND 
                    togther_card_answers.state NOT IN (0, 10) THEN 0
                    ELSE 1
                END
            ) AS dm_message
            """

            dm_chatroom_message_filter_query = """
            WHERE 
            (
                chatroom_data.dm_message = 1
            )
            """

        sql = """
                SELECT chatrooms_data.*, {} FROM
                (SELECT 
                  chat_conversation_data.*, 
                  {} 
                FROM 
                  (
                    SELECT 
                      chatroom_users_data.*, 
                      {}, 
                      Row_number() OVER(
                        partition BY togther_card_answers.card_id 
                        ORDER BY 
                          togther_card_answers.created_at DESC
                      ) AS row_number 
                    FROM 
                      (
                        (
                          SELECT 
                            chat_users_data.*, 
                            {} 
                          FROM 
                            (
                              SELECT 
                                chat_creators_data.*, 
                                {} 
                              FROM 
                                (
                                  SELECT 
                                    chatroom_community_data.*, 
                                    {} 
                                  FROM 
                                    (
                                      SELECT 
                                        chatroom_data.*, 
                                        {} 
                                      FROM 
                                        (
                                          SELECT 
                                            {} {}
                                          FROM 
                                            togther_collabcardstate 
                                            INNER JOIN togther_collabcard ON togther_collabcardstate.card_id = togther_collabcard.id
                                            {} 
                                          WHERE 
                                            (
                                              togther_collabcardstate.user_id = {} 
                                              AND togther_collabcardstate.follow_status = true 
                                              AND togther_collabcardstate.community_id = {} 
                                              AND togther_collabcardstate.remove_id IS NULL 
                                              AND togther_collabcard.type IN {} 
                                              AND togther_collabcard.updated_at >= {} 
                                              AND togther_collabcard.updated_at <= {}
                                            ) 
                                          ORDER BY 
                                            togther_collabcard.updated_at DESC
                                        ) AS chatroom_data 
                                        INNER JOIN togther_community ON chatroom_data.community_id = togther_community.id
                                        {}
                                    ) AS chatroom_community_data
                                    INNER JOIN togther_userinfo ON (
                                      togther_userinfo.user_id_id = chatroom_community_data.user_id
                                    ) 
                                    LEFT JOIN togther_members ON (
                                      chatroom_community_data.user_id = togther_members.member_id_id 
                                      AND chatroom_community_data.community_id = togther_members.community_id_id
                                    )
                                    LEFT JOIN togther_sdkclientusersinfo ON (
                                        chatroom_community_data.user_id = togther_sdkclientusersinfo.user_id
                                        AND chatroom_community_data.community_id = togther_sdkclientusersinfo.community_id
                                    )
                                ) AS chat_creators_data 
                                LEFT JOIN togther_userinfo ON (
                                  togther_userinfo.user_id_id = chat_creators_data.chatroom_with_user_id
                                ) 
                                LEFT JOIN togther_members ON (
                                  chat_creators_data.chatroom_with_user_id = togther_members.member_id_id 
                                  AND chat_creators_data.community_id = togther_members.community_id_id
                                )
                                LEFT JOIN togther_sdkclientusersinfo ON (
                                    chat_creators_data.chatroom_with_user_id = togther_sdkclientusersinfo.user_id
                                    AND chat_creators_data.community_id = togther_sdkclientusersinfo.community_id
                                )
                            ) AS chat_users_data 
                            LEFT JOIN togther_userinfo ON (
                              togther_userinfo.user_id_id = chat_users_data.chat_requested_by_id
                            ) 
                            LEFT JOIN togther_members ON (
                              chat_users_data.chat_requested_by_id = togther_members.member_id_id 
                              AND chat_users_data.community_id = togther_members.community_id_id
                            )
                            LEFT JOIN togther_sdkclientusersinfo ON (
                                chat_users_data.chat_requested_by_id = togther_sdkclientusersinfo.user_id
                                AND chat_users_data.community_id = togther_sdkclientusersinfo.community_id
                            )
                        ) AS chatroom_users_data 
                        INNER JOIN togther_card_answers ON togther_card_answers.card_id = chatroom_users_data.id 
                        AND togther_card_answers.state IN (0, 1, 10)
                        AND NOT (
                            togther_card_answers.attachment_count > 0
                            AND togther_card_answers.attachments_uploaded = False
                        )
                      )
                  ) AS chat_conversation_data 
                  LEFT JOIN togther_userinfo ON (
                    togther_userinfo.user_id_id = chat_conversation_data.conversation___user_id___last
                  )
                  LEFT JOIN togther_members ON (
                    chat_conversation_data.conversation___user_id___last = togther_members.member_id_id
                  AND chat_conversation_data.conversation___community_id___last = togther_members.community_id_id)
                  LEFT JOIN togther_sdkclientusersinfo ON (
                    chat_conversation_data.conversation___user_id___last = togther_sdkclientusersinfo.user_id
                    AND chat_conversation_data.conversation___community_id___last = togther_sdkclientusersinfo.community_id
                  )
                  LEFT JOIN togther_card_answers ON togther_card_answers.id = chat_conversation_data.topic_id 
                WHERE 
                  chat_conversation_data.row_number = 1) AS chatrooms_data
                  
                  LEFT JOIN togther_userinfo ON (
                    togther_userinfo.user_id_id = chatrooms_data.conversation___user_id___topic
                  )
                  LEFT JOIN togther_members ON (
                    chatrooms_data.conversation___user_id___topic = togther_members.member_id_id
                  AND chatrooms_data.conversation___community_id___topic = togther_members.community_id_id)
                  LEFT JOIN togther_sdkclientusersinfo ON (
                     chatrooms_data.conversation___user_id___topic = togther_sdkclientusersinfo.user_id
                     AND chatrooms_data.conversation___community_id___topic = togther_sdkclientusersinfo.community_id
                  )
                
                  ORDER BY chatrooms_data.updated_at DESC offset {} limit {};
        """.format(topic_user_data_query, topic_conversation_data_query,
                   get_conversation_query_meta_for_sync_revamp("last"),
                   chatroom_with_user_data_query, chat_requested_user_data_query, creator_data_query,
                   get_community_query_meta_for_sync_revamp(""), chatroom_query, dm_chatroom_message_query,
                   dm_chatroom_conversation_query, user_id, community_id, included_chatroom_types_query,
                   min_timestamp, max_timestamp, dm_chatroom_message_filter_query, offset, limit)

        if only_query:
            return sql

        conn = get_connection()
        curr = conn.cursor()

        curr.execute(sql)
        chatroom_data = convert_sql_query_result_to_dict(curr, curr.fetchall())
        curr.close()

        chatroom_ids_list = [data.get('id') for data in chatroom_data]

        return chatroom_data, chatroom_ids_list

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_chatroom_conversations_data(user_id, community_id, chatroom_id, min_timestamp: int = None,
                                    max_timestamp: int = None, page: int = 1, limit: int = 10,
                                    only_query: bool = False, is_local_db: bool = True, conversation_id: str = None,
                                    excluded_conversation_states: list = None):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        order_by_query = "last_updated DESC"

        if (min_timestamp > 0) and (max_timestamp > 0):
            order_by_query = "last_updated ASC"

        # If is_local_db is false, then order conversations response by created_at DESC
        if is_local_db is False:
            order_by_query = "created_at DESC"

        conversation_id_query = ""
        excluded_conversation_states_query = ""

        if conversation_id:
            conversation_id_query = "togther_card_answers.id = {} AND".format(conversation_id)

        if excluded_conversation_states:
            excluded_conversation_states_query = "togther_card_answers.state NOT IN {} AND".format(
                get_tuple_from_array_v2(excluded_conversation_states))

        chatroom_data_query = ",".join([get_chatroom_query_meta_for_sync_revamp("conv_room"),
                                        get_chatroom_state_query_meta_for_sync_revamp("conv_room"),
                                        get_community_query_meta_for_sync_revamp("conv_community"),
                                        get_users_query_meta_for_sync_revamp("creator"),
                                        get_members_query_meta_for_sync_revamp("creator"),
                                        get_sdk_client_query_meta_for_sync_revamp("creator"),
                                        get_conversation_query_meta_for_sync_revamp("reply")])

        room_creator = ",".join([get_users_query_meta_for_sync_revamp("room_creator"),
                                 get_members_query_meta_for_sync_revamp("room_creator"),
                                 get_sdk_client_query_meta_for_sync_revamp("room_creator")])

        dm_other_user = ",".join([get_users_query_meta_for_sync_revamp("dm_other_user"),
                                  get_members_query_meta_for_sync_revamp("dm_other_user"),
                                  get_sdk_client_query_meta_for_sync_revamp("dm_other_user")])

        conv_reply_user = ",".join([get_users_query_meta_for_sync_revamp("conv_reply_user"),
                                    get_members_query_meta_for_sync_revamp("conv_reply_user"),
                                    get_sdk_client_query_meta_for_sync_revamp("conv_reply_user")])

        chatroom_meta_query = ",".join([get_users_query_meta_for_sync_revamp("conv_deleter"),
                                        get_members_query_meta_for_sync_revamp("conv_deleter"),
                                        get_sdk_client_query_meta_for_sync_revamp("conv_deleter"),
                                        get_chatroom_query_meta_for_sync_revamp("preview"),
                                        get_community_query_meta_for_sync_revamp("preview")])

        sql = """
                SELECT conv_reply_user_meta.*, {} FROM
                (SELECT chatroom_dm_meta.*, {} FROM
                (SELECT    chatroom_preview_meta.*,
                          {}, {}
                FROM      (
                                    SELECT    chatroom_meta.*,
                                              {}
                                    FROM      (
                                                         SELECT     conversation_data.*,
                                                                    {}
                                                         FROM       (
                                                                             SELECT   {}
                                                                             FROM     togther_card_answers
                                                                             WHERE    ({} {}
                                                                                               togther_card_answers.card_id = {}
                                                                                      AND      togther_card_answers.community_id = {}
                                                                                      AND NOT   ( 
                                                                                                    togther_card_answers.attachment_count > 0
                                                                                                    AND togther_card_answers.attachments_uploaded = False
                                                                                                )
                                                                                      AND      togther_card_answers.last_updated >= {}
                                                                                      AND      togther_card_answers.last_updated <= {} )
                                                                             ORDER BY 
                                                                            togther_card_answers.{}
                                                                             offset {} limit {}) AS conversation_data
                                                         INNER JOIN togther_collabcard
                                                         ON         conversation_data.card_id = togther_collabcard.id
                                                         INNER JOIN togther_collabcardstate
                                                         ON         (
                                                                        togther_collabcardstate.card_id = togther_collabcard.id
                                                                        AND togther_collabcardstate.user_id = {}
                                                                    )
                                                         INNER JOIN togther_community
                                                         ON         conversation_data.community_id = togther_community.id
                                                         INNER JOIN togther_userinfo
                                                         ON         conversation_data.user_id = togther_userinfo.user_id_id
                                                         LEFT JOIN  togther_members
                                                         ON         (
                                                                               conversation_data.user_id = togther_members.member_id_id
                                                                    AND        conversation_data.community_id = togther_members.community_id_id)
                                                         LEFT JOIN togther_sdkclientusersinfo 
                                                         ON         conversation_data.user_id = togther_sdkclientusersinfo.user_id
                                                         LEFT JOIN  togther_card_answers
                                                         ON         conversation_data.reply_id = togther_card_answers.id) AS chatroom_meta
                                    LEFT JOIN togther_userinfo
                                    ON        chatroom_meta.deleted_by_user_id = togther_userinfo.user_id_id
                                    LEFT JOIN togther_members
                                    ON        (
                                                        chatroom_meta.deleted_by_user_id = togther_members.member_id_id
                                              AND       chatroom_meta.community_id = togther_members.community_id_id)
                                    LEFT JOIN togther_sdkclientusersinfo 
                                    ON         chatroom_meta.deleted_by_user_id = togther_sdkclientusersinfo.user_id
                                    LEFT JOIN togther_collabcard
                                    ON        chatroom_meta.preview_chatroom_id = togther_collabcard.id
                                    LEFT JOIN togther_community
                                    ON        chatroom_meta.preview_community_id = togther_community.id) AS chatroom_preview_meta
                INNER JOIN togther_userinfo
                ON         chatroom_preview_meta.chatroom___user_id___conv_room = togther_userinfo.user_id_id
                LEFT JOIN  togther_members
                ON   (
                            chatroom_preview_meta.chatroom___user_id___conv_room = togther_members.member_id_id
                       AND  chatroom_preview_meta.chatroom___community_id___conv_room = togther_members.community_id_id)
                LEFT JOIN togther_sdkclientusersinfo 
                ON         chatroom_preview_meta.chatroom___user_id___conv_room = togther_sdkclientusersinfo.user_id
                LEFT JOIN togther_collabcard
                ON        chatroom_preview_meta.reply_chatroom_id = togther_collabcard.id) AS chatroom_dm_meta
                LEFT JOIN togther_userinfo
                ON         chatroom_dm_meta.chatroom___chatroom_with_user_id___conv_room = 
                togther_userinfo.user_id_id
                LEFT JOIN  togther_members
                ON   (
                            chatroom_dm_meta.chatroom___chatroom_with_user_id___conv_room = togther_members.member_id_id
                       AND  chatroom_dm_meta.chatroom___community_id___conv_room = togther_members.community_id_id)
                LEFT JOIN togther_sdkclientusersinfo 
                ON         chatroom_dm_meta.chatroom___chatroom_with_user_id___conv_room = 
                togther_sdkclientusersinfo.user_id) AS conv_reply_user_meta
                LEFT JOIN togther_userinfo
                ON         conv_reply_user_meta.conversation___user_id___reply = togther_userinfo.user_id_id
                LEFT JOIN  togther_members
                ON   (
                            conv_reply_user_meta.conversation___user_id___reply = togther_members.member_id_id
                       AND  conv_reply_user_meta.conversation___community_id___reply = togther_members.community_id_id)
                LEFT JOIN togther_sdkclientusersinfo 
                ON         conv_reply_user_meta.conversation___user_id___reply = togther_sdkclientusersinfo.user_id 
                ORDER BY conv_reply_user_meta.{};
        """.format(conv_reply_user, dm_other_user, get_chatroom_query_meta_for_sync_revamp("reply"), room_creator,
                   chatroom_meta_query, chatroom_data_query, get_conversation_query_meta_for_sync_revamp(),
                   conversation_id_query, excluded_conversation_states_query, chatroom_id, community_id,
                   min_timestamp, max_timestamp, order_by_query, offset, limit, user_id, order_by_query)

        if only_query:
            return sql

        conn = get_connection()
        curr = conn.cursor()

        curr.execute(sql)
        conversation_data = convert_sql_query_result_to_dict(curr, curr.fetchall())
        curr.close()

        conversation_ids_list = [data.get('id') for data in conversation_data]

        return conversation_data, conversation_ids_list

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_unseen_count_for_chatroom_ids(chatroom_ids_list: list, user_id: int):
    try:
        conn = get_connection()
        curr = conn.cursor()

        chatroom_ids_query = get_tuple_from_array(chatroom_ids_list)

        included_conv_states = [conversation_states.ANSWER, conversation_states.CONVERSATION_HEADER,
                                conversation_states.CONVERSATION_POLL]

        included_conv_states_query = get_tuple_from_array(included_conv_states)

        sql = """
                SELECT state_data.card_id,
                       Sum(state_data.is_unseen)
                FROM   (SELECT togther_collabcardstate.card_id,
                               ( CASE
                                   WHEN COALESCE(last_seen_conversation_id, 0) <
                                        togther_card_answers.id
                                        AND togther_card_answers.state NOT IN ( 1 ) THEN 1
                                   ELSE 0
                                 END ) AS is_unseen
                        FROM   togther_collabcardstate
                               LEFT JOIN togther_card_answers
                                      ON togther_card_answers.card_id =
                                         togther_collabcardstate.card_id
                                      AND NOT (
                                            togther_card_answers.attachment_count > 0
                                            AND togther_card_answers.attachments_uploaded = false
                                      )
                        WHERE  togther_collabcardstate.user_id = {}
                               AND togther_collabcardstate.card_id IN {}
                               AND togther_card_answers.state IN {}) AS state_data
                GROUP  BY state_data.card_id; 
        """.format(user_id, chatroom_ids_query, included_conv_states_query)

        curr.execute(sql)
        chatroom_data = curr.fetchall()
        curr.close()

        return {data[0]: {'unseen_count': data[1]} for data in chatroom_data}

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_reactions_for_chatroom_or_conversations(community_id, reaction_type: int = SyncTypes.CHATROOM,
                                                chatroom_ids: list = None, conversation_ids: list = None,
                                                key_name_prefix: str = None):
    try:
        conn = get_connection()
        curr = conn.cursor()

        reactions_data = []

        if reaction_type == SyncTypes.CHATROOM:

            if (not chatroom_ids) or (not isinstance(chatroom_ids, list)):
                return reactions_data

            chatroom_ids_query = get_tuple_from_array(chatroom_ids)
            query_string = "WHERE chatroom_id IN {} AND conversation_id IS NULL".format(chatroom_ids_query)

        elif reaction_type == SyncTypes.CONVERSATION:

            if (not conversation_ids) or (not isinstance(conversation_ids, list)):
                return reactions_data

            conversation_ids_query = get_tuple_from_array(conversation_ids)
            query_string = "WHERE conversation_id IN {}".format(conversation_ids_query)

        else:
            return reactions_data

        response_query = ",".join([get_reactions_query_meta_for_sync_revamp(key_name_prefix),
                                   get_users_query_meta_for_sync_revamp("reactor"),
                                   get_members_query_meta_for_sync_revamp("reactor"),
                                   get_sdk_client_query_meta_for_sync_revamp("reactor")])

        sql = """
                SELECT {} FROM togther_messagereactions
                LEFT JOIN togther_userinfo ON (
                  togther_userinfo.user_id_id = togther_messagereactions.user_id
                ) 
                LEFT JOIN togther_members ON (
                  togther_messagereactions.user_id = togther_members.member_id_id 
                  AND togther_members.community_id_id = {}
                )
                LEFT JOIN togther_sdkclientusersinfo ON (
                    togther_messagereactions.user_id = togther_sdkclientusersinfo.user_id
                )  {};
        """.format(response_query, community_id, query_string)

        curr.execute(sql)
        reactions_data = convert_sql_query_result_to_dict(curr, curr.fetchall())
        curr.close()

        return reactions_data

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_attachments_data(attachment_type: int = SyncTypes.CHATROOM,
                         chatroom_ids: list = None, conversation_ids: list = None,
                         key_name_prefix: str = None):
    try:
        conn = get_connection()
        curr = conn.cursor()

        attachments_data = []

        if attachment_type == SyncTypes.CHATROOM:

            if (not chatroom_ids) or (not isinstance(chatroom_ids, list)):
                return attachments_data

            chatroom_ids_query = get_tuple_from_array(chatroom_ids)
            sql = "SELECT {} FROM togther_card_attachment WHERE collabcard_id IN {}".format(
                get_card_attachments_query_meta_for_sync_revamp(key_name_prefix), chatroom_ids_query)

        elif attachment_type == SyncTypes.CONVERSATION:

            if (not conversation_ids) or (not isinstance(conversation_ids, list)):
                return attachments_data

            conversation_ids_query = get_tuple_from_array(conversation_ids)
            sql = "SELECT {} FROM togther_answerattachment WHERE answer_id IN {}".format(
                get_conversation_attachments_query_meta_for_sync_revamp(key_name_prefix), conversation_ids_query)

        else:
            return attachments_data

        curr.execute(sql)
        attachments_data = convert_sql_query_result_to_dict(curr, curr.fetchall())
        curr.close()

        return attachments_data

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_conversation_polls_data(community_id, conversation_ids: list, user_id: int, key_name_prefix: str = None):
    try:
        conn = get_connection()
        curr = conn.cursor()

        conversation_ids_query = get_tuple_from_array(conversation_ids)
        poll_data_query = ",".join([get_conversation_polls_query_meta_for_sync_revamp(key_name_prefix),
                                    get_conversation_poll_members_query_meta_for_sync_revamp("voter")])

        poll_options_creator = ",".join([get_users_query_meta_for_sync_revamp("options_creator"),
                                         get_members_query_meta_for_sync_revamp("options_creator"),
                                         get_sdk_client_query_meta_for_sync_revamp("options_creator")])

        sql = """
            SELECT final_polls_data.*, no_votes * 100 / final_polls_data.count AS percentage, {}
            FROM   (SELECT polls_data.conversation_id, id, no_votes, total_voters.count, is_selected, 
                    Split_part(text_options,'___', 1) AS text,
                    Cast(COALESCE(Split_part(poll_option_creator, '___', 1), '0') AS BIGINT) AS user_id
                    FROM   (SELECT conversation_id, id, Sum(vote_count) AS no_votes,
                                   CASE
                                     WHEN Sum(is_selected) > 0 THEN true
                                     ELSE false
                                   END                              AS is_selected,
                                   String_agg(Text(text), '___')    AS text_options,
                                   String_agg(Text(user_id), '___') AS poll_option_creator
                            FROM   (SELECT {},
                                           CASE
                                             WHEN togther_conversationpollmembers.user_id = {}
                                           THEN 1
                                             ELSE 0
                                           END
                                           AS
                                           is_selected,
                                           CASE
                                             WHEN togther_conversationpollmembers.id IS NOT
                                                  NULL
                                           THEN 1
                                             ELSE 0
                                           END
                                           AS
                                           vote_count
                                    FROM   togther_conversationpolls
                                           LEFT JOIN togther_conversationpollmembers
                                                  ON
            togther_conversationpolls.conversation_id =
                           togther_conversationpollmembers.conversation_id
                           AND togther_conversationpolls.id =
                           togther_conversationpollmembers.poll_id
                           WHERE  togther_conversationpolls.conversation_id IN {}) AS polls_all_data
                            GROUP  BY conversation_id,
                                      id) AS polls_data
                            LEFT JOIN (
                                SELECT conversation_id, COUNT(DISTINCT(user_id)) FROM
                                togther_conversationPollMembers GROUP BY conversation_id
                                HAVING conversation_id IN {}) AS total_voters
                                ON total_voters.conversation_id = polls_data.conversation_id
                            ) AS final_polls_data
                   LEFT JOIN togther_userinfo
                          ON ( togther_userinfo.user_id_id = final_polls_data.user_id )
                   LEFT JOIN togther_members
                          ON ( final_polls_data.user_id = togther_members.member_id_id
                               AND togther_members.community_id_id = {})
                   LEFT JOIN togther_sdkclientusersinfo
                          ON ( final_polls_data.user_id = togther_sdkclientusersinfo.user_id );
        """.format(poll_options_creator, poll_data_query, user_id, conversation_ids_query, conversation_ids_query,
                   community_id)

        curr.execute(sql)
        polls_data = convert_sql_query_result_to_dict(curr, curr.fetchall())
        curr.close()

        return polls_data

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_excluded_chatroom_ids_for_notification_settings_for_user(
        user_id, chatroom_ids_list, notification_setting_type: int = noti_states.ONLY_MENTIONS_AND_REPLIES):
    try:
        conn = get_connection()
        curr = conn.cursor()

        if not (chatroom_ids_list and user_id):
            return []

        chatroom_ids_query = get_tuple_from_array(chatroom_ids_list)

        exlcude_computation_query = "0 AS should_exclude"

        if notification_setting_type == noti_states.ONLY_MENTIONS_AND_REPLIES:
            exlcude_computation_query = """
             ( CASE
               WHEN answer ~* '{}' THEN 0
               WHEN answer ~* '{}' THEN 0
               WHEN answer ~* '{}' THEN 0
               ELSE 1
               END ) AS should_exclude
            """.format(SPECIFIC_MEMBER_TAG_REGEX.format(user_id), PARTICIPANTS_TAG_REGEX, EVERYONE_TAG_REGEX)

        sql = """
                SELECT card_id
                FROM   (WITH added_row_number
                             AS (SELECT ca.card_id,
                                        ca.answer,
                                        Row_number()
                                          over(
                                            PARTITION BY ca.card_id
                                            ORDER BY ( CASE WHEN ca.state IN (0) THEN 1 ELSE 2
                                          END),
                                          ca.created_at DESC)
                                        AS row_number
                                 FROM   togther_card_answers AS ca
                                        inner join togther_collabcardstate AS cs
                                                ON ( ca.card_id = cs.card_id
                                                     AND cs.user_id = {} )
                                 WHERE  cs.card_id IN {}
                                        AND cs.noti_state = {})
                        SELECT card_id,
                               answer,
                               {}
                         FROM   added_row_number
                         WHERE  row_number = 1) AS CONV_DATA
                WHERE  CONV_DATA.should_exclude = 1; 
        """.format(user_id, chatroom_ids_query, notification_setting_type, exlcude_computation_query)

        curr.execute(sql)
        card_ids = curr.fetchall()
        curr.close()

        return [card_id[0] for card_id in card_ids]

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_chatroom_invites_for_user(user_id, community_id, chatroom_types: list, invite_status: int,
                                  page: int = 1, limit: int = 10):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        chatroom_types_query = get_tuple_from_array(chatroom_types)

        sql = """
            SELECT togther_chatroominvite.id FROM togther_chatroominvite
            INNER JOIN togther_collabcard
            ON togther_chatroominvite.chatroom_id = togther_collabcard.id
            WHERE (
                togther_collabcard.community_id = {}
                AND togther_collabcard.type IN {}
                AND togther_chatroominvite.invite_receiver_id = {}
                AND togther_chatroominvite.invite_status = {}
            ) 
            ORDER BY togther_chatroominvite.created_at DESC
            OFFSET {} LIMIT {};
        """.format(community_id, chatroom_types_query, user_id, invite_status, offset, limit)

        conn = get_connection()
        curr = conn.cursor()

        curr.execute(sql)
        chatroom_invite_data = curr.fetchall()
        curr.close()

        return [invite_id[0] for invite_id in chatroom_invite_data]
    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_user_chatroom_status(user_id, community_id, chatroom_types: list, page: int = 1, limit: int = 10):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        chatroom_types_query = get_tuple_from_array(chatroom_types)
        chatroom_data_query = ",".join([get_chatroom_query_meta_for_sync_revamp(),
                                        get_chatroom_state_query_meta_for_sync_revamp()])

        sql = """
            SELECT {}, COALESCE(togther_collabcardstate.follow_status, false) AS follow_status 
            FROM togther_collabcard
            LEFT JOIN togther_collabcardstate ON
            (
                togther_collabcard.id = togther_collabcardstate.card_id
                AND togther_collabcardstate.user_id = {}
            ) 
            WHERE 
            (
                togther_collabcard.community_id = {}
                AND togther_collabcard.is_deleted = false
                AND togther_collabcard.type in {}
            )
            ORDER BY togther_collabcard.created_at DESC
            OFFSET {} LIMIT {};
        """.format(chatroom_data_query, user_id, community_id, chatroom_types_query, offset, limit)

        conn = get_connection()
        curr = conn.cursor()

        curr.execute(sql)
        user_chatroom_status_data = convert_sql_query_result_to_dict(curr, curr.fetchall())
        curr.close()

        return user_chatroom_status_data
    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_users_meta_info(community_id, member_ids: list, check_for_user_id=True, user_meta_or_none_dict: bool=False):
    try:
        member_ids = [str(member_id) for member_id in member_ids]
        member_ids_query = get_tuple_from_array_v2(member_ids)

        sql = """
                SELECT togther_userinfo.user_id_id AS user_id,
                       togther_userinfo.user_unique_id,
                       togther_sdkclientusersinfo.user_unique_id AS clients_user_unique_id
                FROM   togther_userinfo
                       INNER JOIN togther_sdkclientusersinfo
                               ON togther_sdkclientusersinfo.user_id =
                                  togther_userinfo.user_id_id
                WHERE  togther_sdkclientusersinfo.community_id = {}
                       AND (togther_sdkclientusersinfo.user_unique_id IN {}
                            OR togther_userinfo.user_unique_id IN {});
        """.format(community_id, member_ids_query, member_ids_query)

        conn = get_connection()
        curr = conn.cursor()

        curr.execute(sql)
        user_meta_info = convert_sql_query_result_to_dict(curr, curr.fetchall())
        curr.close()

        # if user_meta_or_none_dict is True, then return dict of all member_ids with user_meta if exists or None
        if user_meta_or_none_dict:

            uuids = {}
            client_uuids = {}
            users_meta = {}

            # make a dict of user_unique_id and clients_user_unique_id
            for user_meta in user_meta_info:
                uuids[user_meta.get('user_unique_id')] = user_meta 
                client_uuids[user_meta.get('clients_user_unique_id')] = user_meta

            for member_id in member_ids:
                if member_id in uuids:
                    users_meta[member_id] = uuids.get(member_id)

                elif member_id in client_uuids:
                    users_meta[member_id] = client_uuids.get(member_id)

                else: 
                    users_meta[member_id] = None 

            return users_meta

        if check_for_user_id:
            found_user_ids = []
            for user_meta in user_meta_info:
                found_user_ids.append(user_meta["user_unique_id"])
                found_user_ids.append(user_meta["clients_user_unique_id"])

            remaining_member_ids = list(set(member_ids) - set(found_user_ids))
            remaining_member_ids = [user_id for user_id in remaining_member_ids if user_id.isdigit()]

            if not remaining_member_ids:
                return user_meta_info

            remaining_member_ids_query = get_tuple_from_array_v2(remaining_member_ids)

            sql = """
                 SELECT togther_userinfo.user_id_id AS user_id,
                           togther_userinfo.user_unique_id,
                           togther_sdkclientusersinfo.user_unique_id AS clients_user_unique_id
                    FROM   togther_userinfo
                           INNER JOIN togther_sdkclientusersinfo
                                   ON togther_sdkclientusersinfo.user_id =
                                      togther_userinfo.user_id_id
                    WHERE  togther_sdkclientusersinfo.community_id = {}
                           AND togther_userinfo.user_id_id IN {};
            """.format(community_id, remaining_member_ids_query, remaining_member_ids_query)

            conn = get_connection()
            curr = conn.cursor()

            curr.execute(sql)
            user_meta_info.extend(convert_sql_query_result_to_dict(curr, curr.fetchall()))
            curr.close()

        return user_meta_info
    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_ordered_chatrooms_data_on_unseen_count(user_id, community_id: str = None, excluded_card_ids: list = None):
    try:
        conn = get_connection()
        curr = conn.cursor()

        community_id_query = ""
        excluded_card_ids_query = ""

        if community_id:
            community_id_query = "AND togther_collabcardstate.community_id={}".format(community_id)

        if excluded_card_ids:
            excluded_card_ids_query = "AND togther_collabcardstate.card_id NOT IN {}".format(get_tuple_from_array(
                excluded_card_ids))

        included_conv_states = [conversation_states.ANSWER, conversation_states.CONVERSATION_HEADER,
                                conversation_states.CONVERSATION_POLL]

        included_conv_states_query = get_tuple_from_array(included_conv_states)

        sql = """
                SELECT state_data.card_id,
                       Sum(state_data.is_unseen)  AS unseen_count,
                       Max(state_data.created_at) AS last_conversation_epoch,
                       Max(state_data.id)         AS last_conversation
                FROM   (SELECT togther_collabcardstate.card_id,
                               ( CASE
                                   WHEN Coalesce(last_seen_conversation_id, 0) <
                                        togther_card_answers.id
                                        AND togther_card_answers.state NOT IN ( 1 ) THEN 1
                                   ELSE 0
                                 end ) AS is_unseen,
                               togther_card_answers.created_at,
                               togther_card_answers.id
                        FROM   togther_collabcardstate
                               LEFT JOIN togther_card_answers
                                      ON togther_card_answers.card_id =
                                         togther_collabcardstate.card_id
                        WHERE  togther_collabcardstate.user_id = {}
                               AND togther_collabcardstate.follow_status = true
                               AND togther_collabcardstate.remove_id IS NULL {} {}
                               AND togther_card_answers.state IN {}) AS state_data
                WHERE state_data.is_unseen > 0
                GROUP  BY state_data.card_id
                ORDER  BY last_conversation_epoch DESC; 
        """.format(user_id, community_id_query, excluded_card_ids_query, included_conv_states_query)

        curr.execute(sql)
        chatroom_data = curr.fetchall()
        curr.close()

        return {
            data[0]: {
                'unseen_count': data[1],
                'last_conversation_epoch': data[2],
                'last_conversation_id': data[3]
            } for data in chatroom_data}

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)
