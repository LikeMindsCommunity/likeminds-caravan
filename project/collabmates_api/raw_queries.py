from __future__ import absolute_import, unicode_literals
from celery import shared_task
import time
import logging
import psycopg2
from utility.states import card_types

from external_services.logging.logging_wrapper import LoggingWrapper

error_logger = LoggingWrapper.get_instance()
info_logger = LoggingWrapper.get_instance()

envir = False
# from utility.utils import custom_cache
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
        conn.close()


    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


def get_active_chatrooms_count_in_community(community_id, user_id, current_time):
    '''function to get active chatrooms based on community and user'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = """select count(distinct(card_id))  from togther_collabcardState where community_id=%s and user_id=%s  and remove_id is null 
              and (expiry_time is null or expiry_time > %s)
              and card_id in (select id from togther_collabcard where community_id=%s and is_pending=false and is_deleted=false)
              """ % (str(community_id), str(user_id), str(current_time), str(community_id))

        curr.execute(sql)
        count = curr.fetchone()
        curr.close()
        conn.close()

        return count[0]


    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


def get_inactive_chatrooms_count_in_community(community_id, user_id, current_time):
    '''function to get in-active chatrooms based on community and user'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = """select count(distinct(card_id)) from togther_collabcardState where community_id=%s and user_id=%s  and remove_id is null 
        and (expiry_time is not null and expiry_time < %s)
        and card_id in (select id from togther_collabcard where community_id=%s and is_pending=false and is_deleted=false)
        """ % (str(community_id), str(user_id), str(current_time), str(community_id))

        curr.execute(sql)
        count = curr.fetchone()
        curr.close()
        conn.close()

        return count[0]


    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


def get_inactive_followed_chatrooms_count(user_id, current_time):
    '''function to get active chatrooms based on community and user'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = """select count(*) from togther_collabcardState where  user_id=%s and follow_status=True and remove_id is null 
        and (expiry_time is not null and expiry_time < %s)""" % (str(user_id), str(current_time))

        curr.execute(sql)
        count = curr.fetchone()
        curr.close()
        conn.close()

        return count[0]


    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


def get_active_my_chatrooms_count(user_id, current_time):
    '''function to give the count of active my chatrooms'''

    try:

        conn = get_connection()
        curr = conn.cursor()
        sql = """select count(id) from togther_conversationEngage where user_id=%s and card_id  in
                     (select card_id from togther_collabcardState where user_id = %s and follow_status = True and (remove_id is null)
                    and (expiry_time is null or expiry_time > %s) 
                   )""" % (
            str(user_id), str(user_id), str(current_time))

        curr.execute(sql)
        count = curr.fetchone()
        curr.close()
        conn.close()

        return count[0]


    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


def get_active_followed_chatrooms(user_id, current_time, page, limit=10):
    '''function to get the active followed chatroom count'''
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        conn = get_connection()
        curr = conn.cursor()
        sql = """select id from togther_conversationEngage where user_id=%s and card_id  in
                  (select card_id from togther_collabcardState where user_id = %s and follow_status = True and (remove_id is null)
                 and (expiry_time is null or expiry_time > %s) 
                ) order by updated_at desc,id desc limit %s offset %s""" % (
            str(user_id), str(user_id), str(current_time), str(limit), str(offset))

        curr.execute(sql)
        res = curr.fetchall()

        engage_list = []

        for id in res:
            engage_list.append(id[0])
        curr.close()
        conn.close()

        return engage_list


    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


def get_inactive_followed_chatrooms(user_id, current_time, page, limit=10):
    '''function to get the active followed chatroom count'''
    try:
        page_number = int(page)
        offset = (page_number - 1) * limit

        conn = get_connection()
        curr = conn.cursor()
        sql = """select id from togther_conversationEngage where user_id=%s and card_id  in
                  (select card_id from togther_collabcardState where user_id = %s and follow_status = True and (remove_id is null)
                 and (expiry_time is not null and expiry_time <= %s) 
                ) order by updated_at desc,id desc limit %s offset %s""" % (
            str(user_id), str(user_id), str(current_time), str(limit), str(offset))

        curr.execute(sql)
        res = curr.fetchall()

        engage_list = []

        for id in res:
            engage_list.append(id[0])
        curr.close()
        conn.close()

        return engage_list


    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


def get_draft_chatrooms_on_home_screen(user_id, page, limit=10):
    '''api to get draft chatroom home-screen'''

    try:
        page_number = int(page)
        limit = 10
        offset = (page_number - 1) * 10

        conn = get_connection()
        curr = conn.cursor()
        sql = """select id,card_id,draft_id from togther_conversationEngage where user_id=%s order by updated_at desc,id desc limit %s offset %s""" % (
            str(user_id), str(limit), str(offset))

        curr.execute(sql)
        res = curr.fetchall()

        draft_list = []

        for data in res:
            if data[2]:
                draft_list.append(data[0])
        curr.close()
        conn.close()

        return draft_list


    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


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
        conn.close()


    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


def get_all_data(sql):
    '''function to get all data based on a sql query'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        curr.execute(sql)
        res = curr.fetchall()
        curr.close()
        conn.close()
        if res:
            return res
        return []

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


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
        conn.close()
    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting  to PostgreSQL", error)


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
        conn.close()
        info_logger.info("Record deleted successfully for user:,", user_id)
    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting  to PostgreSQL", error)


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


def fetch_chatrooms_query(user_id, limit, page, last_updated):
    '''function to update chatroom data'''

    try:
        conn = get_connection()
        curr = conn.cursor()

        offset = (int(page) - 1) * int(limit)

        last_updated = int(last_updated)
        if not last_updated:
            sql = """
            SELECT 
            togther_collabcard.id,
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
            togther_collabcardState.is_guest,
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
            togther_collabcard.location_long
            from togther_collabcard
            INNER JOIN togther_collabcardState
            ON togther_collabcardState.card_id = togther_collabcard.id 
            INNER JOIN togther_community
            ON togther_community.id = togther_collabcard.community_id
            where togther_collabcardState.user_id=%s  and togther_collabcardState.remove_id is null order by togther_collabcardState.id  limit  %s  offset %s """ % (
                str(user_id), str(limit), str(offset))
        else:
            sql = """
                   SELECT 
                   togther_collabcard.id,
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
                   togther_collabcardState.is_guest,
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
                   togther_collabcard.location_long
                   from togther_collabcard
                   INNER JOIN togther_collabcardState
                   ON togther_collabcardState.card_id = togther_collabcard.id 
                   INNER JOIN togther_community
                   ON togther_community.id = togther_collabcard.community_id
                   where togther_collabcardState.user_id=%s and togther_collabcardState.remove_id is null
                   and togther_collabcardState.updated_at > %s order by togther_collabcardState.id  limit  %s  offset %s""" % (
                str(user_id), str(last_updated), str(limit), str(offset))

        curr.execute(sql)
        data = curr.fetchall()
        curr.close()
        conn.close()
        chatroom_id_list = get_chatroom_id_list(data)

        return data, chatroom_id_list

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


def fetch_chatroom_polls(chatroom_id_list):
    '''function to update chatroom data'''

    try:
        conn = get_connection()
        curr = conn.cursor()

        if len(chatroom_id_list) == 1:
            chatroom_ids = "(" + str(chatroom_id_list[0]) + ")"
        else:
            chatroom_ids = tuple(chatroom_id_list)
        sql = """select 
                togther_collabcardPolls.card_id, 
                togther_collabcardPolls.id, 
                togther_collabcardPolls.text, 
                togther_collabcardPolls.image_url,
                togther_collabcardPolls.sub_text, 
                togther_collabcardPolls.user_id,
                togther_userinfo.name,
                togther_userinfo.image_link
                from togther_collabcardPolls 
                inner join togther_userinfo on 
                togther_collabcardPolls.user_id = togther_userinfo.user_id_id where
                togther_collabcardPolls.card_id in %s 
                order by togther_collabcardPolls.id
            """ % (str(chatroom_ids))

        curr.execute(sql)

        data = curr.fetchall()
        curr.close()
        conn.close()
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

        sql = """select card_id,poll_id,user_id from togther_memberPollVotes where card_id in %s""" % (
            str(chatroom_ids))
        curr.execute(sql)
        data = curr.fetchall()
        curr.close()
        conn.close()
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
        error_logger.error("Error while connecting to PostgreSQL  ", error)


def fetch_chatroom_id_query(chatroom_id, user_id):
    try:
        conn = get_connection()
        curr = conn.cursor()

        sql = """
            SELECT 
            togther_collabcard.id,
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
            togther_collabcardState.is_guest,
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
            togther_collabcard.location_long
            from togther_collabcard
            INNER JOIN togther_collabcardState
            ON togther_collabcardState.card_id = togther_collabcard.id 
            INNER JOIN togther_community
            ON togther_community.id = togther_collabcard.community_id
            where togther_collabcardState.user_id=%s 
            and togther_collabcardState.card_id=%s 
            and togther_collabcardState.remove_id is null """ % (
            str(user_id), str(chatroom_id))

        curr.execute(sql)
        data = curr.fetchall()
        curr.close()
        conn.close()
        chatroom_id_list = get_chatroom_id_list(data)
        return data, chatroom_id_list


    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


def fetch_community_chatroom_query(community_id, user_id, page, limit):
    try:
        conn = get_connection()
        curr = conn.cursor()

        offset = (int(page) - 1) * int(limit)
        sql = """
            SELECT 
            togther_collabcard.id,
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
            togther_collabcardState.is_guest,
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
            togther_collabcard.location_long
            from togther_collabcard
            INNER JOIN togther_collabcardState
            ON togther_collabcardState.card_id = togther_collabcard.id 
            INNER JOIN togther_community
            ON togther_community.id = togther_collabcard.community_id
            where  togther_collabcard.community_id=%s and togther_collabcardState.user_id = %s
            and togther_collabcardState.remove_id is null 
            order by id limit %s offset %s """ % (
            str(community_id), str(user_id), str(limit), str(offset))

        curr.execute(sql)
        data = curr.fetchall()
        curr.close()
        conn.close()

        chatroom_id_list = get_chatroom_id_list(data)

        return data, chatroom_id_list
    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


def get_chatroom_id_list(data):
    chatroom_id_list = []
    for card in data:
        if card[8] == card_types.CARD_POLL:
            chatroom_id_list.append(card[0])

    return chatroom_id_list


def get_community_id_list(member_id):
    """function to give community id list of member"""

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = """select community_id_id from togther_members where member_id_id=%s""" % (str(member_id))
        curr.execute(sql)
        curr.execute(sql)
        data = curr.fetchall()
        curr.close()
        conn.close()
        community_id_list = []

        for community_id in data:
            community_id_list.append(community_id[0])

        return community_id_list

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


def get_members_of_community(community_id_list, last_updated, page, limit):
    """function to get members of the community present in community_id list"""

    try:
        conn = get_connection()
        curr = conn.cursor()
        community_id_tupple = get_tuple_from_array(community_id_list)
        offset = (int(page) - 1) * int(limit)

        sql = """select togther_members.member_id_id,
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
                                from togther_members
                                INNER JOIN togther_userinfo 
                                ON togther_members.member_id_id = togther_userinfo.user_id_id
                                INNER JOIN togther_community
                                ON togther_community.id = togther_members.community_id_id
                                WHERE togther_members.community_id_id in  %s and togther_members.updated_at > %s
                                limit %s offset %s
                """ % (str(community_id_tupple), last_updated, limit, offset)

        curr.execute(sql)
        curr.execute(sql)
        res = curr.fetchall()
        curr.close()
        conn.close()
        member_date = process_member_data(res)

        return member_date

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


def get_member_responses_for_community(community_id_list):
    """check if member has responses in the community and returns a dictionary"""

    try:
        conn = get_connection()
        curr = conn.cursor()
        community_id_tupple = get_tuple_from_array(community_id_list)

        sql = """select  member_id, community_id from togther_communityAnswers where community_id in  %s """ % (
            str(community_id_tupple))
        curr.execute(sql)
        curr.execute(sql)
        res = curr.fetchall()
        curr.close()
        conn.close()
        responses_dict = get_dictionary_of_member_responses(res)

        return responses_dict

    except (Exception, psycopg2.Error) as error:
        error_logger.error("Error while connecting to PostgreSQL  ", error)


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


if envir:
    if __name__ == "__main__":
        info_logger.info("python file")
        start_time = time.time()
        ranking_all_users_and_communities()

        end_time = time.time()

        info_logger.info("Execution Time--")
        info_logger.info(end_time - start_time)
