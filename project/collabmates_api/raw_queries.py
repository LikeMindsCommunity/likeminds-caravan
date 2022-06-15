from __future__ import absolute_import, unicode_literals
from celery import shared_task
import time
import logging
import psycopg2
from utility.states import card_types, conversation_states
from utility.utils import is_version_code_supported_for_intro_room

from external_services.logging.logging_wrapper import LoggingWrapper

from utility.time_utilities import TimeUtilities
from .utility import create_chatroom_revamp_version_check

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
        conn = get_connection()
        curr = conn.cursor()

        sql = """update togther_conversationengage set last_conversation_id = %s ,unseen_count = %s where card_id=%s and user_id = %s"""
        paramter_list = [last_conversation_id, unseen_count, card_id, user_id]
        curr.execute(sql, paramter_list)
        conn.commit()
        info_logger.info("conversation engage updated successfully")
        curr.close()

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)


def get_my_chatrooms_count(user_id,
                           version_code,
                           platform_code,
                           consider_dm_chatrooms=False,
                           dm_instance_community_ids_list=[],
                           community_id=None,
                           intro_room_community_list=[]):
    '''function to give the count of active my chatrooms'''
    try:
        is_private = "FALSE"
        chatroom_with_user_id_val = "NULL"
        dm_chatrooms_communities_filter = ""

        if community_id:
            dm_chatrooms_communities_filter = f"AND community_id IN ({str(community_id)})"

        if consider_dm_chatrooms and len(dm_instance_community_ids_list) == 0:
            return 0

        if consider_dm_chatrooms and len(dm_instance_community_ids_list) != 0:
            is_private = "TRUE"
            chatroom_with_user_id_val = "NOT NULL"
            dm_chatrooms_communities_filter = "AND community_id IN (%s)" % ",".join([
                str(i) for i in dm_instance_community_ids_list])

        if is_version_code_supported_for_intro_room(version_code, platform_code):

            if intro_room_community_list:
                intro_filter_list_str = ",".join([str(i) for i in intro_room_community_list])
                filter_intro_rooms_query = """
                CASE WHEN community_id IN ( %s ) THEN user_id != %s
                                                AND type = 1
                ELSE type IN ( 1, 9 ) END
                """ % (intro_filter_list_str, user_id)

            else:
                filter_intro_rooms_query = """type IN ( 1, 9 )"""

        else:
            filter_intro_rooms_query = """type = -1"""

        excluded_card_ids_filter = """"""
        if create_chatroom_revamp_version_check(platform_code, version_code):
            excluded_card_ids = get_card_ids_to_exclude_based_on_cohort_access(user_id, community_id=community_id)
            if excluded_card_ids:
                excluded_card_ids_filter = "AND id NOT IN (%s)" % ",".join([str(card_id) for card_id in excluded_card_ids])

        conn = get_connection()
        curr = conn.cursor()

        sql = """SELECT Count(id)
                FROM   togther_conversationengage
                WHERE  user_id = %s
                       AND card_id IN (SELECT card_id
                                       FROM   togther_collabcardstate
                                       WHERE  user_id = %s
                                              AND follow_status = TRUE
                                              AND ( remove_id IS NULL )
                                              AND secret_chatroom_left = FALSE
                                              AND card_id IN (SELECT id
                                                              FROM   togther_collabcard
                                                              WHERE  (is_private = %s
                                                                     AND is_private_member = FALSE
                                                                     AND not (%s)
                                                                     AND chatroom_with_user_id
                                                                         IS %s %s) %s)

                  ) """ % (
            str(user_id),
            str(user_id),
            is_private,
            str(filter_intro_rooms_query),
            chatroom_with_user_id_val,
            dm_chatrooms_communities_filter,
            excluded_card_ids_filter
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


def get_followed_chatrooms(user_id,
                           page,
                           version_code,
                           platform_code,
                           limit=10,
                           consider_dm_chatrooms=False,
                           dm_instance_community_ids_list=[],
                           community_id=None,
                           intro_room_community_list=[]):
    '''function to get the active followed chatroom count'''
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        is_private_val = "FALSE"
        chatroom_with_user_val = "NULL"
        dm_chatrooms_communities_filter = ""

        if community_id:
            dm_chatrooms_communities_filter = f"AND community_id IN ({str(community_id)})"

        if consider_dm_chatrooms and len(dm_instance_community_ids_list) == 0:
            return []

        if consider_dm_chatrooms and len(dm_instance_community_ids_list) != 0:
            is_private_val = "TRUE"
            chatroom_with_user_val = "NOT NULL"
            dm_chatrooms_communities_filter = "AND community_id IN (%s)" % ",".join([
                str(i) for i in dm_instance_community_ids_list])

        if is_version_code_supported_for_intro_room(version_code, platform_code):

            if intro_room_community_list:
                intro_filter_list_str = ",".join([str(i) for i in intro_room_community_list])
                filter_intro_rooms_query = """
                CASE WHEN community_id IN ( %s ) THEN user_id != %s
                                                AND type = 1
                ELSE type IN ( 1, 9 ) END
                """ % (intro_filter_list_str, user_id)

            else:
                filter_intro_rooms_query = """type IN ( 1, 9 )"""

        else:
            filter_intro_rooms_query = """type = -1"""

        excluded_card_ids_filter = """"""
        if create_chatroom_revamp_version_check(platform_code, version_code):
            excluded_card_ids = get_card_ids_to_exclude_based_on_cohort_access(user_id, community_id=community_id)
            if excluded_card_ids:
                excluded_card_ids_filter = "AND id NOT IN (%s)" % ",".join([str(card_id) for card_id in excluded_card_ids])

        conn = get_connection()
        curr = conn.cursor()

        sql = """SELECT   id
                FROM     togther_conversationengage
                WHERE    user_id=%s
                AND      card_id IN
                         (
                                SELECT card_id
                                FROM   togther_collabcardstate
                                WHERE  user_id = %s
                                AND    follow_status = true
                                AND    (
                                              remove_id IS NULL)
                                AND    secret_chatroom_left=false
                                AND    card_id IN
                                       (
                                              SELECT id
                                              FROM   togther_collabcard
                                              WHERE  (is_private = %s
                                              AND is_private_member = FALSE
                                              AND not (%s)
                                              AND    chatroom_with_user_id IS %s %s) %s))
                ORDER BY updated_at DESC,
                         id DESC limit %s offset %s""" % (
            str(user_id),
            str(user_id),
            str(is_private_val),
            str(filter_intro_rooms_query),
            str(chatroom_with_user_val),
            str(dm_chatrooms_communities_filter),
            str(excluded_card_ids_filter),
            str(limit),
            str(offset))

        curr.execute(sql)
        res = curr.fetchall()

        engage_list = []
        for id in res:
            engage_list.append(id[0])

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
                    togther_collabcardState.chat_request_created_at
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
                     togther_community.name
            FROM togther_members
            INNER JOIN togther_userinfo
                ON togther_members.member_id_id = togther_userinfo.user_id_id
            INNER JOIN togther_community
                ON togther_community.id = togther_members.community_id_id
            WHERE togther_members.community_id_id IN %s
                    AND togther_members.updated_at > %s order by 
                    togther_members.updated_at  limit %s offset %s
            
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
                     togther_community.name
            FROM togther_members
            INNER JOIN togther_userinfo
                ON togther_members.member_id_id = togther_userinfo.user_id_id
            INNER JOIN togther_community
                ON togther_community.id = togther_members.community_id_id
            WHERE togther_members.member_id_id IN %s
                    AND togther_members.updated_at > %s 
                    AND togther_members.community_id_id = %s order by updated_at limit %s offset %s

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
        member_data.append(temp)

    return member_data


def get_tuple_from_array(array):
    if len(array) == 1:
        tupp = "(" + str(array[0]) + ")"

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


def get_members_based_on_user_list_query(user_list, community_id, order_by_name=False):
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
                         "togther_members"."created_at"
                FROM "togther_members"
                INNER JOIN "togther_userinfo"
                    ON ("togther_members"."member_id_id" = "togther_userinfo"."user_id_id")
                WHERE ("togther_members"."community_id_id" = %s
                        AND "togther_members"."member_id_id" IN %s)""" % (str(community_id), str(user_tupple))

        if order_by_name:
            sql += " order by lower(togther_userinfo.name) ASC"

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
            member_list.append(member_dict)

        return member_list

    except (Exception, psycopg2.Error) as error:
        print(error)
        error_logger.error("Error while connecting to PostgreSQL %s ", error)

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


def get_chatroom_count_based_on_community_list(community_id_list, member_id) -> {}:
    try:
        conn = get_connection()
        curr = conn.cursor()

        community_id_tupple = get_tuple_from_array(community_id_list)

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
                        AND NOT ("togther_collabcard"."type" in (%s, %s, %s))
                        AND ("togther_collabcard"."is_private" = FALSE)
                        AND ("togther_collabcard"."chatroom_with_user_id" is NULL))
                GROUP BY  togther_collabcardstate.community_id
                HAVING "togther_collabcardstate".community_id IN %s""" \
              % (str(member_id), str(card_types.CARD_INTRO), str(card_types.CARD_EVENT),
                 str(card_types.CARD_PUBLIC_EVENT), str(community_id_tupple))

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

        print(sql)

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
            SELECT    togther_collabcard.id
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
                      OR        togther_card_answers.attachments_uploaded = true)
            GROUP BY  togther_collabcard.id
            ORDER BY  count(togther_card_answers.card_id) DESC limit {} offset {};
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


def get_dm_chatrooms_of_user(user_id, community_id):
    try:
        conn = get_connection()
        curr = conn.cursor()

        if isinstance(community_id, list):
            community_id = "IN (" + ",".join([str(i) for i in community_id]) + ")"
        else:
            community_id = "=" + str(community_id)

        sql = """SELECT CS.card_id, CS.id
                   FROM   togther_collabcardstate AS CS
                   WHERE  CS.follow_status = true
                          AND CS.remove_id IS NULL
                          AND CS.secret_chatroom_left = false
                          AND CS.user_id = %s
                          AND card_id IN (SELECT id
                                          FROM   togther_collabcard
                                                 AS
                                                 CCRD
                                          WHERE
                              CCRD.community_id %s
                              AND is_private = true
                              AND CCRD.type = 10
                              AND ( CCRD.user_id = %s OR
                              CCRD.chatroom_with_user_id = %s ))
        """ % (str(user_id), str(community_id), str(user_id), str(user_id))

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


def get_last_conversation_id_corresponding_to_chatrooms_list(chatrooms_list, page=1, limit=10):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit
        
        card_tuple = get_tuple_from_array(chatrooms_list)
        
        conn = get_connection()
        curr = conn.cursor()

        sql = """WITH added_row_number
                 AS (SELECT CA.created_at,
                            CA.id,
                            CA.card_id,
                            Row_number()
                              OVER(
                                partition BY CA.card_id
                                ORDER BY CA.created_at DESC) AS row_number
                                FROM togther_card_answers as CA
                                WHERE  CA.card_id IN %s)
            SELECT card_id, id
            FROM   added_row_number
            WHERE  row_number = 1
            ORDER  BY created_at DESC LIMIT %s OFFSET %s; 
        """ % (card_tuple, str(limit), str(offset))
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

        raw_data = "CS.card_id, CA.id, CA.state"
        additional_filter = ""

        if not data_state:
            raw_data = "Count(*)"
            additional_filter = "AND CA.state IN (0, 13, 14, 15, 16, 17, 19, 20)"

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


def get_all_chatrooms_of_community(user_id, community_id, page=1, limit=10):
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        conn = get_connection()
        curr = conn.cursor()

        sql = """SELECT id
                 FROM  togther_collabcard
                 WHERE (user_id=%s
                       AND is_private = false
                       AND community_id = %s 
                       AND type NOT IN (10))
                 OFFSET %s LIMIT %s;""" % (str(user_id), str(community_id), str(offset), str(limit))

        curr.execute(sql)
        card_list = curr.fetchall()
        curr.close()

        return [data[0] for data in card_list]

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL %s ", error)
