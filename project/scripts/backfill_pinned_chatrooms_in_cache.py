import time

from togther.models import (ModelUtilities, Community, Collabcard)
from utility.cache_keys import (COMMUNITY_PINNED_CHATROOMS_LIST_CACHE_KEY)
from external_services.caching.cache_impl import CacheImpl


def backfill_pinned_chatrooms_in_cache():
    all_communities = ModelUtilities.get_model_filter(Community, {})

    for community in all_communities:
        pinned_chatrooms_list = list(set(ModelUtilities.get_model_filter(
            Collabcard, {'community': community, 'is_pinned': True, 'is_deleted': False}).values_list('id', flat=True)))

        if not pinned_chatrooms_list:
            continue

        key = COMMUNITY_PINNED_CHATROOMS_LIST_CACHE_KEY.format(community.id)
        CacheImpl.set_cache(key, {'pinned_chatrooms': pinned_chatrooms_list})


print('Starting script')
start = time.time()
backfill_pinned_chatrooms_in_cache()
print('Completed in', time.time() - start)
