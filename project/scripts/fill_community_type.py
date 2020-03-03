from utility.community_type.py import CommunityType
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
        communities = Community.objects.all()
        for community in communities:
            community_type_class.post(community_instance=community)
            time.sleep(2)


fill_community_types(community_id=48391)