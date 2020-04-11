import time
from togther.models import Community, communityQuestions,Collabcard,Members,\
    Member_Engage,temp_admin,communityAnswers,Community_Rank,collabcardTemp
from django.db.models import Count, Q
import json
import ast
from django.db import connection


def get_iitd_communities():

    '''function to get iitd communities ids'''

    cursor = connection.cursor()


    sql = """(SELECT id FROM togther_community WHERE name LIKE '%IIT%' and id<174)  order by id"""
    cursor.execute(sql)

    res=cursor.fetchall()

    community_ids=[]

    for id in res:
        community_ids.append(id[0])
    print(community_ids)
    return community_ids


def delete_data_for_iid_communities(community_ids):

    '''function to delete collabcard_state'''
    #community_ids = [49]
    for community_id in community_ids:

        collabcard_delete = Collabcard.objects.filter(community_id=community_id).delete()
        print("collabcard_delete--",collabcard_delete)

        members_delete = Members.objects.filter(community_id=community_id).delete()
        print("members_delete--",members_delete)

        members_engage_delete = Member_Engage.objects.filter(community_id=community_id).delete()
        print("members_engage_delete--",members_engage_delete)

        community_answers_delete = communityAnswers.objects.filter(community_id=community_id).delete()
        print("community_answers_delete---",community_answers_delete)


        temp_admin_delete = temp_admin.objects.filter(community_id=community_id).delete()
        print("temp_admin_delete---", temp_admin_delete)

        community_rank_delete = Community_Rank.objects.filter(community_id=community_id).delete()
        print("community_rank_delete--",community_rank_delete)

        update_status=communityQuestions.objects.filter(community_id=community_id,question_state=0).update(question_state=4)
        print("community_update_status",update_status)

        # delete_status=communityQuestions.objects.filter(community_id=community_id,question_state=7).delete()
        # print("question status--",delete_status)

        temp = collabcardTemp.objects.filter(community_id=community_id).delete()
        print("temp--",temp)




        community_instances = Community.objects.filter(id=community_id)

        if community_instances.exists():

            community_instance = community_instances[0]

            community_instance.hide_community = '3'
            community_instance.purpose_collabcard = None
            community_instance.members_count = 0
            community_instance.save()
            print("community_instance--",community_instance)

            has_intro = communityQuestions.objects.filter(question_title="Community Bio",
                                                        question_state=7,community=community_instance)
            if not has_intro.exists():
                questions_instance = communityQuestions()
                questions_instance.community = community_instance
                questions_instance.question_title = "Community Bio"
                questions_instance.question_state = 7
                questions_instance.value = """[{"min_chars":"50","max_chars":"200"}]"""
                questions_instance.optional = False
                questions_instance.help_text = """Introduce yourself to the community"""
                questions_instance.save()

                print("question_instance--",questions_instance)
        print("\n\n")



# ans = get_iitd_communities()
# print(ans)
start_time = time.time()

community_ids = get_iitd_communities()
delete_data_for_iid_communities(community_ids)

end_time=time.time()
diff=end_time-start_time
print("script time--",diff)