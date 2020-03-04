from utility.community_type import CommunityType
from togther.models import (Community, Community_Legacy,
                            Community_Profession, Community_Interest,
                            Community_Geography, Tags_lpig,
                            Category, Attributes)
import time

def fill_community_types(community_id=None):

    community_type_class = CommunityType()
    if community_id:
        community_type_class.post(community_id=community_id)

    else:
        print("all communities")
        communities = Community.objects.all().order_by("id")

        for community in communities:
            print("community id == ", community.id , "  >>>  ",
                  community_type_class.post(community_instance=community, response_type = 'string'))
            # community_type_class.post(community_instance=community)
            # time.sleep(2)

print("community type script started ")
# fill_community_types(community_id=48391)

fill_community_types()
print("community type script ended")

