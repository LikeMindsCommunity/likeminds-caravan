from utility.states import (member_states)
from togther.models import (Members, userMemberRights, Community, memberRights, ModelUtilities)
from django.db.models import Q
import time

# Community id (Replace it for which rights need to be backfilled)
community_id = None 

# Rights to be backfilled
rights = [
    1, #1: create chatroom
    2, #2: create polls
    3, #3: create events
    4, #4: respond in chatroom     
    6  #6: Auto-approve created chat rooms
    ] 
  
def give_right_to_members_with_no_right(community_id:int, right:int):

    print(f"Processing community: {community_id} for right: {right}")

    community_instance = ModelUtilities.get_model_instance_or_none(Community, community_id)
    right_instance = ModelUtilities.get_model_instance_or_none(memberRights, right)

    if not right_instance:
        print(f"Right with id: {right} does not exist")
        return False

    if not community_instance:
        print(f"Community with id: {community_id} does not exist")
        return False

    members_with_right = userMemberRights.objects.filter(community=community_instance, right=right).values_list('user', flat=True)
    
    community_members = Members.objects.select_related("member_id"
                                                           ).filter(community_id=community_id
                                                                    ).filter(Q(state=member_states.MEMBER) |
                                                                             Q(state=member_states.KNOWN_NOMINATED_PROMOTER) |
                                                                             Q(state=member_states.PROFILE_UNAVAILABLE)
                                                                             )
    
    members_with_no_right = community_members.exclude(member_id__in=members_with_right)
    
    print(f"Total members with right: {members_with_right.count()} and members with no right: {members_with_no_right.count()}")

    userMemberRights_instances = []

    for member in members_with_no_right:
        userMemberRights_instance = userMemberRights(community=community_instance, 
                                                     user=member.member_id,
                                                     right=right_instance)
        
        userMemberRights_instances.append(userMemberRights_instance)

    # Bulk create instances
    if len(userMemberRights_instances):
       print(f"Creating {len(userMemberRights_instances)} instances for right: {right} for community: {community_id}")
       ModelUtilities.bulk_create_instances(userMemberRights, userMemberRights_instances)
   
    return True

def backfill_rights_for_all_members_of_a_community(community_id:int, rights:list):

    start_time = time.time()

    for right in rights:
        print("***********************************************")
        give_right_to_members_with_no_right(community_id, right)
        print("***********************************************")

    print("completed in " , str(time.time() - start_time))

# Call backfill function to backfill rights for members of a community
backfill_rights_for_all_members_of_a_community(community_id, rights)
