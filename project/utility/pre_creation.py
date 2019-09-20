from __future__ import absolute_import, unicode_literals
from celery import shared_task
import psycopg2
import json
import requests as rqst
import time
from datetime import date
import re
envir=False
try:
    from collabmates_api.notification import get_connection
    from utility.utils import get_city_address
    print("try statement")
except:
    envir=True
    import sys
    sys.path.append("..")
    from project.wsgi import *
    from scripts.connection import get_connection
    from utility.utils import get_city_address
    print("except statement")


def get_attribute_data(attribute_id):

    '''function that will give the global id to the user'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "select name,tag_characterstics,tag_image,tag_id from togther_tags_lpig where attribute_id_id="+str(attribute_id)+" order by id desc"
        curr.execute(sql)
        res = curr.fetchall()
        curr.close()
        conn.close()
        if res:
            return res

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)


def is_community_tags_exists(temp):

    '''function to check the tags for that particular community'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        sql="""select community_id_id from togther_community_legacy where tags_id_id=%s
                and community_id_id in (select community_id_id from togther_community_profession where tags_id_id=%s)
                and community_id_id in (select community_id_id from togther_community_interest where tags_id_id=%s)
                and community_id_id in (select community_id_id from togther_community_geography where tags_id_id=%s)
                """%(temp['tags']['legacy'],temp['tags']['profession'],temp['tags']['interest'],temp['tags']['geography'])
        curr.execute(sql)
        res=curr.fetchall()
        curr.close()
        conn.close()
        if res:
            return res[0][0]


    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)


def get_tag_by_id(id):

    '''function to get tag by id'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "select name,tag_characterstics,tag_image,id,attribute_id_id from togther_tags_lpig where id=%s"
        parameter = [id]
        curr.execute(sql, parameter)
        res=curr.fetchall()
        conn.commit()
        curr.close()
        conn.close()
        if res:
            return res
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)


def get_tag_by_name(name):

    '''function to get Tag by name'''

    if not name:
        return False

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "select tag_id,tag_characterstics,tag_image,tag_id,attribute_id_id from togther_tags_lpig where name=%s"
        parameter = [name]
        curr.execute(sql, parameter)
        res=curr.fetchone()
        conn.commit()
        curr.close()
        conn.close()
        if res:
            return res
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)

def create_tag(name,attribute_id):

    '''function to create a tag'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "insert into togther_tags_lpig(name,attribute_id_id,category_id_id,tag_image) values(%s,%s,%s,%s) RETURNING id"
        parameter = [name,attribute_id,5,'']
        curr.execute(sql, parameter)
        conn.commit()
        id = curr.fetchone()[0]
        update_correct_tag_id(id)
        curr.close()
        conn.close()
        return id

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)

def update_correct_tag_id(tag_id):

    '''function to update the tag'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        sql="update togther_tags_lpig set tag_id=%s where id=%s"
        parameter = [tag_id, tag_id]
        curr.execute(sql, parameter)
        conn.commit()
        curr.close()
        conn.close()

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)


def capitalize_string(s):
  return re.sub('(?<=^)[a-z]|(?<=\s)[a-z]', '{}', s).format(*map(str.upper, re.findall('(?<=^)[a-z]|(?<=\s)[a-z]', s)))


def college_city(legacy_college,geography_city):

    '''function to make legacy(college) and geography(city) community '''



    for college in legacy_college:
        for city in geography_city:
            temp={}
            temp['tags']={
                'interest':17,
                'profession':16
            }
            if college[1] is not None:
                name=json.loads(college[1])
                if 'demonym' in name and name['demonym']:
                    temp['name']=name['demonym'] + " in " + city[0]
                    temp['purpose']="For "+ str(temp['name']) + " to socialise and help each other"
                    temp['question']="Introduce yourself telling a bit about your time at " + str(college[0])+" and what do you do now?"
                elif 'csn' in name and name['csn']:
                    temp['name']=name['csn'] + " Alumni in " + city[0]
                    temp['purpose']="For "+ str(temp['name']) + " to socialise and help each other"
                    temp['question']="Introduce yourself telling a bit about your time at " + str(name['csn'])+" and what do you do now?"
                else:
                    temp['name'] = college[0] + " Alumni  in " + city[0]
                    temp['purpose'] = "For " + str(temp['name']) + " to socialise and help each other"
                    temp['question'] = "Introduce yourself telling a bit about your time at " + str(college[0])+" and what do you do now?"

            else:
                temp['name']=college[0] + " Alumni  in " + city[0]
                temp['purpose']="For "+ str(temp['name']) + " to socialise and help each other"
                temp['question']="Introduce yourself telling a bit about your time at " + str(college[0])+" and what do you do now?"

            temp['about']="""This community aims to bring together alumni of %s living in %s so that we can socialise with other and stay connected with our alma mater as well. Here we collaborate with each other by sharing knowledge, providing referrals for jobs, accommodation, business, etc. and having meaningful conversations. We also use this space to plan offline meetups.
                            Anytime if you are looking for a lead or offering some help, simply start a new conversation with relevant details and your ask from the community members. Relevant members can respond by simply chatting with you and each other on your conversation card. 
                            Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.Please try to maintain conversations for each query or discussion on the conversation card so that only relevant members get notifications and all the conversations get documented for future reference of members of this community."""%(college[0],city[0])
            temp['geography']=str(city[0])

            if college[2]:
                temp['image_url']=college[2]
            temp['tags']['legacy']=college[3]
            temp['tags']['geography']=city[3]

            community_id=is_community_tags_exists(temp)
            if not community_id:
                insert_pre_create_community(temp)

            else:
                update_pre_created_community(community_id,temp)



    print("L(college)G(City) communities created\n")


def hometown_city(legacy_hometown,geography_city):

    '''function to make legacy(hometown) and geography(city) community '''

    # legacy_hometown=[]
    # geography_city=[]
    for hometown in legacy_hometown:
        for city in geography_city:
            temp={}
            temp['tags'] = {
                'interest': 17,
                'profession': 16
            }

            home=get_city_address(hometown[0])
            current=get_city_address(city[0])
            home_place=""
            if home['country'] and current['country'] and home['country'] != current['country']:
                if hometown[1] is not None:
                    data=json.loads(hometown[1])
                    if 'home_demonym' in data and data['home_demonym']:
                        temp['name']=data['home_demonym'] + " in "+city[0]
                    else:
                        temp['name']="Natives of "+str(home['country'])+" in "+str(city[0])
                else:
                    temp['name']="Natives of "+str(home['country'])+" in "+str(city[0])
                temp['question']="""Introduce yourself telling a bit about your time in %s and what brought you to %s and what do you do now?"""%(home['country'],city[0])
                temp['about']="""This community aims to bring together %s so that we can socialise with other. Here we collaborate with each other by sharing knowledge, providing referrals (for jobs, accommodation, business, etc.), planning trips to %s, and having meaningful conversations. We also use this space to plan offline meetups.
                            Anytime if you are looking for a lead or offering some help, simply start a new conversation with relevant details and your ask from the community members. Relevant members can respond by simply chatting with you and each other on your conversation card. Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.
                            Please try to maintain conversations for each query or discussion on the conversation card so that only relevant members get notifications and all the conversations get documented for future reference of members of this community."""%(temp['name'],home['country'])
                home_place=home['country']
            elif home['state'] and current['state'] and home['state']!=current['state']:
                if hometown[1] is not None:
                    data = json.loads(hometown[1])
                    if 'home_demonym' in data and data['home_demonym']:
                        temp['name'] = data['home_demonym'] + " in " + city[0]
                    else:
                        temp['name'] = "Natives of " + str(home['state']) + " in " + str(city[0])
                else:
                    temp['name'] = "Natives of " + str(home['state']) + " in " + str(city[0])
                temp['question']="""Introduce yourself telling a bit about your time in %s and what brought you to %s and what do you do now?"""%(home['state'],city[0])
                temp['about'] = """This community aims to bring together %s so that we can socialise with other. Here we collaborate with each other by sharing knowledge, providing referrals (for jobs, accommodation, business, etc.), planning trips to %s, and having meaningful conversations. We also use this space to plan offline meetups.
                            Anytime if you are looking for a lead or offering some help, simply start a new conversation with relevant details and your ask from the community members. Relevant members can respond by simply chatting with you and each other on your conversation card. Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.
                            Please try to maintain conversations for each query or discussion on the conversation card so that only relevant members get notifications and all the conversations get documented for future reference of members of this community.""" % (
                temp['name'], home['state'])
                home_place=home['state']
            else:

                if not home['city']:
                    continue
                if hometown[1] is not None:
                    data = json.loads(hometown[1])
                    if 'home_demonym' in data and data['home_demonym']:
                        temp['name'] = data['home_demonym'] + " in " + city[0]
                    else:
                        temp['name'] = "Natives of " + str(home['city']) + " in " + str(city[0])
                else:
                    temp['name']="Natives of " + str(home['city']) + " in " + str(city[0])
                temp['question']="""Introduce yourself telling a bit about your time in %s and what brought you to %s and what do you do now?"""%(home['city'],city[0])
                temp['about'] = """This community aims to bring together %s so that we can socialise with other. Here we collaborate with each other by sharing knowledge, providing referrals (for jobs, accommodation, business, etc.), planning trips to %s, and having meaningful conversations. We also use this space to plan offline meetups.
                            Anytime if you are looking for a lead or offering some help, simply start a new conversation with relevant details and your ask from the community members. Relevant members can respond by simply chatting with you and each other on your conversation card. Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.
                            Please try to maintain conversations for each query or discussion on the conversation card so that only relevant members get notifications and all the conversations get documented for future reference of members of this community.""" % (
                    temp['name'], home['city'])

            if str(home['city']) == str(city[0]):
                continue
      
            tag_name=get_tag_by_name(home_place)
            if home_place != hometown[0] and home_place:

                if tag_name:
                    temp['tags']['legacy'] = tag_name[0]
                    if tag_name[2]:
                        temp['image_url']=tag_name[2]
                    if tag_name[1] is not None:
                        data=json.loads(tag_name[1])
                        if data['demonym']:
                            temp['name']=data['demonym'] + " in " + city[0]
                            temp['question'] = """Introduce yourself telling a bit about your time in %s and what brought you to %s and what do you do now?""" % (
                            home_place, city[0])
                            temp['about'] = """This community aims to bring together %s so that we can socialise with other. Here we collaborate with each other by sharing knowledge, providing referrals (for jobs, accommodation, business, etc.), planning trips to %s, and having meaningful conversations. We also use this space to plan offline meetups.
                            Anytime if you are looking for a lead or offering some help, simply start a new conversation with relevant details and your ask from the community members. Relevant members can respond by simply chatting with you and each other on your conversation card. Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.
                            Please try to maintain conversations for each query or discussion on the conversation card so that only relevant members get notifications and all the conversations get documented for future reference of members of this community.""" % (
                                temp['name'], home_place)

            else:
                temp['tags']['legacy'] = hometown[3]
                if hometown[2]:
                    temp['image_url'] = hometown[2]
            temp['tags']['geography'] = city[3]

            temp['purpose']="""For %s to socialise and help each other"""%(temp['name'])

            temp['geography']=str(city[0])
            community_id = is_community_tags_exists(temp)
            if not community_id:
                insert_pre_create_community(temp)
            else:
                update_pre_created_community(community_id, temp)


    print("L(hometown)G(City) communities created\n")


def college_skill(legacy_college,industry_skill):

    '''function to make legacy(college) and Profession(skill) community '''


    for college in legacy_college:
        for skill in industry_skill:
            temp={}
            temp['tags'] = {
                'interest': 17,
                'geography': 18
            }
            skill_expert= str(skill[0]) + " experts"
            if college[1] is not None and skill[1] is not None:
                leg_char=json.loads(college[1])
                prof_char=json.loads(skill[1])
                if 'csn' in leg_char and leg_char['csn'] and 'skill_experts' in prof_char and prof_char['skill_experts']:
                    temp['name']=leg_char['csn'] + " " +capitalize_string(prof_char['skill_experts'])
                    skill_expert = prof_char['skill_experts']
                elif 'csn' in leg_char and leg_char['csn']:
                    temp['name'] = leg_char['csn'] + " "+ capitalize_string(str(skill[0]))
                else:
                    temp['name']=str(college[0])+" Alumni in "+capitalize_string(str(skill[0]))
            elif college[1] is not None:
                leg_char=json.loads(college[1])
                if 'csn' in leg_char and leg_char['csn']:
                    temp['name'] = leg_char['csn'] + " Alumni in "+ capitalize_string(str(skill[0]))
            elif skill[1] is not None:
                prof_char=json.loads(skill[1])
                print(prof_char)
                temp['name'] = str(college[0]) + " " + capitalize_string(str(prof_char['skill_experts']))

            else:
                temp['name']=str(college[0])+" Alumni in "+capitalize_string(str(skill[0]))

            skill_name=skill[0]
            if skill[1] is not None:
                prof_char = json.loads(skill[1])
                if 'skill_name' in prof_char and prof_char['skill_name']:
                    skill_name=prof_char['skill_name']
            temp['purpose']="""For %s from %s to exchange knowledge and referrals"""%(skill_name,college[0])
            temp['question']="""Introduce yourself telling a bit about your background in %s"""%(skill_name)

            temp['about']="""This community is exclusively for %s who studied at %s living across the globe. Here we exchange information, knowledge, documents and important links related to %s and have conversations on the same. We also use this space to help each other by providing referrals (for jobs, business introductions etc.), collaborate on projects and plan offline meetups.
                            Anytime if you are looking for a lead or offering some help, simply start a new conversation with relevant details and your ask from the community members. Relevant members can respond by simply chatting with you and each other on your conversation card. Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.
                            Please try to maintain conversations for each query or discussion on the conversation card so that only relevant members get notifications and all the conversations get documented for future reference of members of this community."""%(skill_expert,college[0],skill_name)
            temp['geography']='Global'
            if skill[2]:
                temp['image_url'] = skill[2]

            temp['tags']['legacy'] = college[3]
            temp['tags']['profession'] = skill[3]
            community_id = is_community_tags_exists(temp)
            if not community_id:
                insert_pre_create_community(temp)
            else:
                update_pre_created_community(community_id, temp)

    print("L(college)P(skill) communities created\n")


def college_industry(legacy_college,profession_industry):

    '''function to make legacy(college) and profession(industry)'''




    for college in legacy_college:
        for industry in profession_industry:
            temp={}
            temp['tags'] = {
                'interest': 17,
                'geography': 18
            }
            print(industry[1])
            if industry[1] is not None:
                prof_char=json.loads(industry[1])
                if prof_char['industry_name']:
                    name=prof_char['industry_name']
                else:
                    name=industry[0]
            else:
                name=industry[0]

            if college[1] is not None:
                leg_char=json.loads(college[1])
                if 'csn' in leg_char and leg_char['csn']:
                    temp['name']=leg_char['csn']+" Alumni in "+capitalize_string(name)
                else:
                    temp['name'] = str(college[0]) + " Alumni in " + capitalize_string(name)

            else:
                temp['name'] = str(college[0]) + " Alumni in " + capitalize_string(name)
            industry_name=industry[0]
            if industry[1] is not None:
                prof_char=json.loads(industry[1])
                if 'industry_name' in prof_char and prof_char['industry_name']:
                    industry_name=prof_char['industry_name']

            temp['purpose']="""For %s alumni working in %s industry to  exchange knowledge and referrals"""%(college[0],industry_name)
            temp['question']="""Introduce yourself telling a bit about your background in %s"""%(industry_name)
            temp['about']="""This community aims to bring together %s alumni working in the %s industry so that we can collaborate with each other. Here we exchange information, knowledge, documents and important links related to %s and have conversations on the same. We also use this space to help each other by providing referrals (for jobs, business introductions etc.), collaborate on projects and plan offline meetups.
                            Anytime if you are looking for a lead or offering some help, simply start a new conversation with relevant details and your ask from the community members. Relevant members can respond by simply chatting with you and each other on your conversation card. Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.
                            Please try to maintain conversations for each query or discussion on the conversation card so that only relevant members get notifications and all the responses get documented for future reference of members of this community."""%(college[0],industry_name,industry_name)
            temp['geography']='Global'
            if industry[2]:
                temp['image_url'] = industry[2]
            temp['tags']['legacy'] = college[3]
            temp['tags']['profession'] = industry[3]
            community_id = is_community_tags_exists(temp)
            if not community_id:
                insert_pre_create_community(temp)
            else:
                update_pre_created_community(community_id, temp)

    print("L(college)P(Industry) communities created\n")


def hobby_city(interest_hobby,geography_city):

    '''function to make interest(hobby) and geography(city)'''



    for hobby in interest_hobby:
        for city in geography_city:
            temp = {}
            temp['tags'] = {
                'legacy': 15,
                'profession': 16
            }
            if hobby[1] is not None:
                interest_char = json.loads(hobby[1])
                if not interest_char['hobbyists']:
                    interest_char['hobbyists']=hobby[0]+" enthusiasts"
                    name=hobby[0]+" enthusiasts"
                    temp['name']=capitalize_string(name)+" of "+ capitalize_string(str(city[0]))
                    interest_char['hobbyists']=interest_char['hobbyists'].lower()
                else:
                    name=str(interest_char['hobbyists'])
                    temp['name']=capitalize_string(name)+" of "+ capitalize_string(str(city[0]))

                if not interest_char['hobby_group_used_case']:
                    interest_char['hobby_group_used_case']="to pursue the hobby together"

                if not interest_char['hobby_group_event']:
                    interest_char['hobby_group_event']="connect with you for something"

                if not interest_char['hobby_event']:
                    interest_char['hobby_event']="query"

                hobby_name=hobby[0]
                if 'hobby_name' in interest_char and interest_char['hobby_name']:
                    hobby_name=hobby[0].lower()

                temp['purpose']="""For %s enthusiasts living in %s to find other %s in their neighbourhood and %s"""%(hobby_name,city[0],interest_char['hobbyists'],interest_char['hobby_group_used_case'])
                temp['about']="""We believe that every %s enthusiast should be able to find other %s whenever he or she wants to %s. This community aims to bring together all the %s enthusiasts living in %s to find other %s in their neighbourhood so that we can achieve this together.
                            Anytime if you are looking for people to %s, simply start a new conversation with relevant details and your ask from the community. Interested members can respond by simply chatting with you and each other on your conversation card. Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.
                            Please try to maintain conversations for each %s on the conversation card for the %s so that only relevant members get notifications."""%(hobby_name,interest_char['hobbyists'],interest_char['hobby_group_used_case'],hobby_name,city[0],interest_char['hobbyists'],interest_char['hobby_group_event'],interest_char['hobby_event'],interest_char['hobby_event'])
                temp['question']="""Introduce yourself telling a bit about your interest or skill level in %s"""%(hobby_name)

            else:

                temp['name'] = str(hobby[0])+" Enthusiasts of "+ str(city[0])
                temp['purpose']="""For %s enthusiasts living in %s to find other %s enthusiasts in their neighbourhood to pursue the hobby together"""%(hobby[0],city[0],hobby[0])

                temp['about']="""We beleive that every %s enthusiast should be able to find other %s enthusiast whenever he or she wants to pursue the hobby together . This community aims to bring together all the %s enthusiasts living in %s to find other %s in their neighbourhood so that we can solve this problem together.
                            Anytime if you are looking for people to connect with you for something , simply start a new conversation with relevant details and your ask from the community. Interested members can respond by simply chatting with you and each other on your conversation card. Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.
                            Please try to maintain conversations for each query  on the conversation card for the query  so that only relevant members get notifications."""%(hobby[0],hobby[0],hobby[0],city[0],hobby[0])
                temp['question']="""Introduce yourself telling a bit about your interest or skill level in %s"""%(hobby[0])

            temp['geography']=city[0]

            if hobby[2]:
                temp['image_url'] = hobby[2]
            temp['tags']['interest'] = hobby[3]
            temp['tags']['geography'] = city[3]
            community_id = is_community_tags_exists(temp)
            if not community_id:
                insert_pre_create_community(temp)
            else:
                update_pre_created_community(community_id, temp)

    print("I(hobby)G(city) communities created\n")


def sport_city(interest_sport,geography_city):

    '''function to make interest(sport) and geography(city)'''

    for sport in interest_sport:
        for city in geography_city:
            temp = {}
            temp['tags'] = {
                'legacy': 15,
                'profession': 16
            }
            if sport[1] is not None:
                interest_char = json.loads(sport[1])

                if not interest_char[ 'sport_players']:
                    interest_char['sport_players']=sport[0]+" enthusiasts"
                    temp['name'] = capitalize_string(str(sport[0])) + " Enthusiasts of " + capitalize_string(str(city[0]))
                    interest_char['sport_players']=interest_char['sport_players'].lower()

                else:
                    players=str(interest_char['sport_players'])
                    temp['name'] =capitalize_string(players) + " of " + capitalize_string(str(city[0]))

                if not interest_char[ 'sport_usecase']:
                    interest_char['sport_usecase']="play the sport"
                else:
                    interest_char['sport_usecase']=interest_char['sport_usecase'].lower()


                if not interest_char['sport_event']:
                    interest_char['sport_event']="match"
                sport_name=sport[0].lower()
                temp['purpose']="""For %s enthusiasts living in %s to find other %s in their neighbourhood and %s """%(sport_name,city[0],interest_char[ 'sport_players'],interest_char['sport_usecase'])
                temp['about']="""We believe that every %s enthusiast should be able to find other %s whenever he or she wants to %s. This community aims to bring together all the %s enthusiasts living in %s so that we can solve this problem together.
                            Anytime if you are looking for people to join you for a %s, simply start a new conversation with the time, venue details, and the type of people you are looking for. Interested members can respond by simply chatting with you and each other on your conversation card. Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.
                            Please try to maintain conversations for each %s on the conversation card for that %s so that only relevant members get notifications."""%(sport_name,interest_char[ 'sport_players'],interest_char[ 'sport_usecase'],sport_name,city[0],interest_char[ 'sport_event'],interest_char[ 'sport_event'],interest_char[ 'sport_event'])
            else:
                temp['name'] = """%s Enthusiasts of %s""" % (sport[0], city[0])
                sport_name=sport[0].lower()
                temp['purpose'] = """For %s enthusiasts living in %s to find other %s enthusiasts in their neighbourhood to play together""" % (
                    sport_name, city[0], sport_name)

                temp['about'] = """We believe that every %s enthusiast should be able to find other %s enthusiasts whenever he or she wants to play the sport. This community aims to bring together all the %s enthusiasts living in %s so that we can solve this problem together.
                            Anytime if you are looking for people to join you for a game, simply start a new conversation with the time, venue details, and the type of people you are looking for. Interested members can respond by simply chatting with you and each other on your conversation card. Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.
                            Please try to maintain conversations for each game on the conversation card for that game so that only relevant members get notifications.""" % (
                    sport_name, sport_name, sport_name, city[0],
                )
            temp['question'] = """Introduce yourself telling a bit about your skill level in %s""" % (
                sport_name)
            temp['geography'] = city[0]
            if sport[2]:
                temp['image_url'] = sport[2]
            temp['tags']['interest'] = sport[3]
            temp['tags']['geography'] = city[3]
            community_id = is_community_tags_exists(temp)
            if not community_id:
                insert_pre_create_community(temp)
            else:
                update_pre_created_community(community_id, temp)

    print("I(sports)G(city) communities created\n")


def fan_city(interest_fan,geography_city):

    '''function to make interest(fan) and geography(city)'''

    for fan in interest_fan:
        for city in geography_city:
            temp = {}
            temp['tags'] ={
                'legacy': 15,
                'profession': 16
            }
            if fan[1] is not None:
                interest_char = json.loads(fan[1])

                if not interest_char['thing_event']:
                    interest_char['thing_event']="discussion or event"

                if not interest_char['thing_fans']:
                    interest_char['thing_fans']=str(fan[0])+" fans"
                    temp['name']=capitalize_string(str(fan[0]))+" Fans of "+capitalize_string(str(city[0]))
                    interest_char['thing_fans']=interest_char['thing_fans'].lower()
                else:
                    thing_fan=interest_char['thing_fans']
                    temp['name'] = """%s of %s""" % (capitalize_string(thing_fan), city[0])
                    interest_char['thing_fans']=interest_char['thing_fans'].lower()
                if not interest_char['thing_group_use_case']:
                    interest_char['thing_group_use_case']="plan hangouts and have conversations around "+interest_char['thing']

                temp['purpose']="""For %s living in %s to find other %s in their neighbourhood to  %s"""%(interest_char['thing_fans'],city[0],interest_char['thing_fans'],interest_char['thing_group_use_case'])
                temp['about'] = """We believe that every %s fanatic should be able to find other %s  whenever he or she wants to %s. This community aims to bring together all the %s  living in %s so that we can achieve this.
                            Anytime if you are looking for people to join you for a %s , simply start a new conversation with the time, venue details, and the type of people you are looking for. Interested members can respond by simply chatting with you and each other on your conversation card. Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.
                            Please try to maintain conversations for each %s  on the conversation card for the %s  so that only relevant members get notifications.""" % (
                    interest_char['thing'], interest_char['thing_fans'],interest_char['thing_group_use_case'],
                    interest_char['thing_fans'], city[0],interest_char['thing_event'],interest_char['thing_event'],interest_char['thing_event']
                )

            else:
                interest_char={}
                interest_char['thing']=fan[0]
                temp['name'] = """%s Fans of %s""" % (interest_char['thing'], city[0])

                temp['purpose'] = """For %s enthusiasts living in %s to find other %s enthusiasts in their neighbourhood and  follow their passion""" % (
                interest_char['thing'], city[0],interest_char['thing'])
                temp['about'] = """We believe that every %s fanatic should be able to find other %s fans whenever he or she wants to follow their passion together. This community aims to bring together all the %s fanatics living in %s so that we can achieve this.
                            Anytime if you are looking for people to join you for a discussion or event , simply start a new conversation with the time, venue details, and the type of people you are looking for. Interested members can respond by simply chatting with you and each other your conversation card. Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.
                            Please try to maintain conversations for each discussion or event  on the conversation card for the discussion or event  so that only relevant members get notifications.""" % (
                interest_char['thing'], interest_char['thing'],
                interest_char['thing'], city[0],
                )
            if fan[2]:
                temp['image_url'] = fan[2]
            temp['tags']['interest'] = fan[3]
            temp['tags']['geography'] = city[3]
            temp['geography'] = city[0]
            fan_ques=fan[0].lower()
            temp['question'] = """Introduce yourself telling a bit about your passion for %s""" % (
               interest_char['thing'])
            community_id = is_community_tags_exists(temp)
            if not community_id:
                insert_pre_create_community(temp)
            else:
                update_pre_created_community(community_id, temp)

    print("I(fan)G(city) communities created\n")


def cause_city(interest_cause,geography_city):

    '''function to make interest(cause) and geography(city)'''

    cause_city=[]
    for cause in interest_cause:
        for city in geography_city:
            temp = {}
            temp['tags'] = {
                'legacy': 15,
                'profession': 16
            }
            if cause[1] is not None:
                interest_char = json.loads(cause[1])
                if 'thing_event' in interest_char and interest_char['thing_event']:
                    temp['name']="""%s  for %s"""%(capitalize_string(city[0]),capitalize_string(cause[0]))
                    cause_name=cause[0].lower()
                    temp['purpose']="""For responsible citizens of %s who are willing to work on %s to plan, meet and work together for the cause"""%(city[0],cause_name)
                    temp['question']="""Introduce yourself telling a bit about your interest or experience in working for %s"""%(cause_name)
                    temp['about']="""Every cause is better served if people working towards it come together. Not just it gives us a sense of belongingness, but also makes it more fun thus increasing our motivation as well. This community aims to bring together all the residents of %s who are working or willing to work on %s so that we can fight for this cause together.
                            Anytime if you are planning to do something for %s and are looking for people to join you, simply start a new conversation with the time, venue details, and the type of people you are looking for. Interested members can respond by simply chatting with you and each other on your conversation card. Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.
                            Please try to maintain conversations for each %s on the conversation card for the %s so that only relevant members get notifications."""%(city[0],cause_name,cause_name,interest_char['thing_event'],interest_char['thing_event'])
                    temp['geography']=city[0]
                    cause_city.append(temp)
                else:
                    interest_char = {}
                    interest_char['thing_event'] = "discussions or event"
                    temp['name'] = """%s for %s""" % (city[0], cause[0])
                    cause_name=cause[0].lower()
                    temp['purpose'] = """For responsible citizens of %s willing to work for %s to plan, meet and work together for the cause""" % (
                        city[0], cause_name)
                    temp[
                        'question'] = """Introduce yourself telling a bit about your interest or experience in working for %s""" % (
                        cause_name)
                    temp['about'] = """Every cause is better served if people working towards it come together. Not just it gives us a sense of belongingness, but also makes it more fun thus increasing our motivation as well. This community aims to bring together all the residents of %s who are working or willing to work for %s so that we can fight for this cause together.
                            Anytime if you are planning to do something for %s and are looking for people to join you, simply start a new conversation with the time, venue details, and the type of people you are looking for. Interested members can respond by simply chatting with you and each other on your conversation card. Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.
                            Please try to maintain conversations for each %s on the conversation card for the %s so that only relevant members get notifications.""" % (
                        city[0], cause_name, cause_name, interest_char['thing_event'], interest_char['thing_event'])
                    temp['geography'] = city[0]
            else:
                interest_char = {}
                interest_char['thing_event']="discussions or event"
                temp['name'] = """%s Residents For %s""" % (city[0], cause[0])
                cause_name = cause[0].lower()
                temp['purpose'] = """For responsible citizens of %s willing to work for %s to plan, meet and work together for the cause""" % (
                city[0], cause_name)
                temp['question'] = """Introduce yourself telling a bit about your interest or experience of working for %s""" % (
                cause_name)
                temp['about'] = """Every cause is better served if people working towards it come together. Not just it gives us a sense of belongingness, but also makes it more fun thus increasing our motivation as well. This community aims to bring together all the residents of %s who are working or willing to work for %s so that we can fight for this cause together.
                            Anytime if you are planning to do something for %s and are looking for people to join you, simply start a new conversation with the time, venue details, and the type of people you are looking for. Interested members can respond by simply chatting with you and each other on your conversation card. Members who want to follow the conversation can press the Follow button to receive notifications about future responses on the card.
                            Please try to maintain conversations for each %s on the conversation card for the %s so that only relevant members get notifications.""" % (
                city[0], cause_name, cause_name, interest_char['thing_event'], interest_char['thing_event'])
                temp['geography'] = city[0]
            if cause[2]:
                temp['image_url'] = cause[2]
            temp['tags']['interest'] = cause[3]
            temp['tags']['geography'] = city[3]

            community_id = is_community_tags_exists(temp)
            if not community_id:
                insert_pre_create_community(temp)
            else:
                update_pre_created_community(community_id, temp)

    print("I(cause)G(city) communities created\n")

@shared_task
def pre_create_communities(tag_id=0):

    '''function to pre create communities'''
    #legacy tags
    legacy_college = get_attribute_data(2)
    legacy_hometown = get_attribute_data(3)



    geography_city = get_attribute_data(12)


    #profession tags
    profession_industry = get_attribute_data(6)
    industry_skill = get_attribute_data(5)


    #interest tags
    interest_hobby = get_attribute_data(9)
    interest_sport = get_attribute_data(10)
    interest_fan = get_attribute_data(11)
    interest_cause = get_attribute_data(8)
    if tag_id:
        tags_data=get_tag_by_id(tag_id)
        attribute_id=tags_data[0][4]
        if attribute_id is 2:                                            #college
            legacy_college=tags_data
            college_city(legacy_college, geography_city)
            college_industry(legacy_college, profession_industry)
            college_skill(legacy_college, industry_skill)


        elif attribute_id is 12:                                          #city

            geography_city=tags_data

            college_city(legacy_college, geography_city)

            hometown_city(legacy_hometown, geography_city)

            hobby_city(interest_hobby, geography_city)

            sport_city(interest_sport, geography_city)

            fan_city(interest_fan, geography_city)

            cause_city(interest_cause, geography_city)



        elif attribute_id is 3:                                          #hometown

            legacy_hometown=tags_data
            hometown_city(legacy_hometown, geography_city)




        elif attribute_id is 5:                                          #skill

            industry_skill=tags_data
            college_skill(legacy_college, industry_skill)


        elif attribute_id is 6:                                         # industry

            profession_industry = tags_data
            college_industry(legacy_college, profession_industry)


        elif attribute_id is 9:                                         #hobby

            interest_hobby=tags_data
            hobby_city(interest_hobby, geography_city)


        elif attribute_id is 10:                                        #sport

            interest_sport=tags_data
            sport_city(interest_sport, geography_city)


        elif attribute_id is 11:                                        #fan

            interest_fan=tags_data
            fan_city(interest_fan, geography_city)


        elif attribute_id is 8:                                         #cause

            interest_cause=tags_data
            cause_city(interest_cause, geography_city)


    else:

        college_city(legacy_college,geography_city)

        hometown_city(legacy_hometown,geography_city)

        college_skill(legacy_college,industry_skill)

        college_industry(legacy_college,profession_industry)

        hobby_city(interest_hobby,geography_city)

        sport_city(interest_sport,geography_city)

        fan_city(interest_fan,geography_city)

        cause_city(interest_cause,geography_city)

def insert_pre_create_community(community):

    '''function to insert pre created communities in database'''
    if 'image_url' not in community:
        community['image_url'] = 'media/community/default.jpeg'

    community['created_at']=time.time()
    community['updated_at']=time.time()
    community['member_count']=0
    today=date.today()
    d=today.strftime("%Y-%m-%d")
    community['active_since']=d
    print(community['name'])
    print("\n\n")
    try:
        conn = get_connection()
        curr = conn.cursor()
        hide_community='3'
        # inserting the communities
        sql="insert into togther_community(name,about,purpose,location,created_at,updated_at,image_url,members_count,active_since,hide_community,introduction_text) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id;"
        parameter_list=[community['name'],community['about'],community['purpose'],community['geography'],community['created_at'],community['updated_at'],community['image_url'],community['member_count'],
                        community['active_since'],hide_community,community['question']]
        curr.execute(sql, parameter_list)
        conn.commit()
        count = curr.rowcount
        print(count, "Record inserted successfully for %s "%(community['name']))


        community_id=curr.fetchone()[0]


        # inserting the questions
        sql="insert into togther_form_data(data,data_type,community_id_id) values(%s,%s,%s)"
        parameter_list=[community['question'],'text',community_id]
        curr.execute(sql, parameter_list)
        conn.commit()
        count = curr.rowcount
        print(count, "Questions inserted successfully for %s" % (community['name']))


        # #inserting the tags in community tags lpig table

        sql = "insert into togther_community_legacy(tags_id_id,community_id_id) values(%s,%s)"
        parameter=[community['tags']['legacy'],community_id]
        insert_tags_for_communities(sql,parameter)

        sql = "insert into togther_community_profession(tags_id_id,community_id_id) values(%s,%s)"
        parameter = [community['tags']['profession'], community_id]
        insert_tags_for_communities(sql, parameter)

        sql = "insert into togther_community_interest(tags_id_id,community_id_id) values(%s,%s)"
        parameter = [community['tags']['interest'], community_id]
        insert_tags_for_communities(sql, parameter)

        sql = "insert into togther_community_geography(tags_id_id,community_id_id) values(%s,%s)"
        parameter = [community['tags']['geography'], community_id]
        insert_tags_for_communities(sql, parameter)

        count = curr.rowcount
        print(count, "Tags inserted successfully for %s" % (community['name']))

        curr.close()
        conn.close()
    except (Exception, psycopg2.Error) as error:
        print(error)
        print("Error while connecting  to PostgreSQL", error)


def update_pre_created_community(community_id,community):

    '''function to update the community if its characterstics or image are changed'''

    has_members=get_members_of_community(community_id)

    if has_members:
        print("Some Members are already present")
        return

    if 'image_url' not in community:
        community['image_url'] = 'media/community/default.jpeg'
    print(community['name'])
    print("\n\n")

    try:
        conn = get_connection()
        curr = conn.cursor()
        updated_at=time.time()
        hide_community='3'
        # inserting the communities
        sql = "update togther_community set name=%s,about=%s,purpose=%s,location=%s,image_url=%s,updated_at=%s,hide_community=%s,introduction_text=%s where id=%s"
        parameter_list = [community['name'], community['about'], community['purpose'], community['geography'],
                          community['image_url'],updated_at,hide_community,community['question'],community_id
                         ]
        curr.execute(sql, parameter_list)
        conn.commit()
        count = curr.rowcount
        print(count, "Record updated successfully into %s " % (community['name']))



        # inserting the questions
        sql = "update togther_form_data set data=%s where community_id_id=%s"
        parameter_list = [community['question'],community_id]
        curr.execute(sql, parameter_list)
        conn.commit()
        count = curr.rowcount
        print(count, "Questions updated successfully for %s" % (community['name']))
        curr.close()
        conn.close()
        print("\n")
    except (Exception, psycopg2.Error) as error:
        print("Error while connecting  to PostgreSQL", error)


def get_members_of_community(community_id):
    '''function to get members of community if exist'''
    try:
        conn = get_connection()
        curr = conn.cursor()
        sql = "select member_id_id,state from togther_members where community_id_id=%s"
        curr.execute(sql,[community_id])
        res = curr.fetchall()
        curr.close()
        conn.close()
        if res:
            return res

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)


def insert_tags_for_communities(sql,parameter):

    '''function to insert community tags based on sql'''

    try:
        conn = get_connection()
        curr = conn.cursor()
        curr.execute(sql, parameter)
        conn.commit()
        count = curr.rowcount
        print(count, "Record inserted successfully")
        curr.close()
        conn.close()

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL  ", error)


if envir:
    if __name__=="__main__":

        pre_create_communities()


