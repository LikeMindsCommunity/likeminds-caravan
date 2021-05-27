from django.db.models import Q
from togther.models import Community, Members
import time


def get_communities_having_member_relation():
    community_list = list(set(Members.objects.values_list('community_id', flat=True)))

    print("community_list", community_list)
    print("useful community count", len(community_list))

    return community_list


def divide_chunks(community_list, chunk_size=1000):
    for i in range(0, len(community_list), chunk_size):
        yield community_list[i:i + chunk_size]


def delete_communities_from_db():
    community_list = get_communities_having_member_relation()

    all_deleted_community_id_list = list(Community.objects.filter(~Q(id__in=community_list)
                                                                  ).values_list('id', flat=True).order_by('id'))

    print("all_deleted_community_id_list", len(all_deleted_community_id_list))

    deleted_chunk_list = list(divide_chunks(all_deleted_community_id_list))

    for id_list in deleted_chunk_list:
        deleted_communities = Community.objects.filter(id__in=id_list).delete()
        print(deleted_communities)
        print()
        time.sleep(2)


start_time = time.time()
delete_communities_from_db()
end_time = time.time()

print(end_time - start_time)
