import time

from togther.models import ModelUtilities, card_answers
from collabmates_api.sdk.models import (SdkClient)
from collabmates_api.search.conversation_index import ConversationDocument

def get_conversation_instances_of_a_community(community_id):
    """
    Get all conversations instances in a community
    """

    conversation_instances = card_answers.objects.filter(community=community_id, is_deleted=False)

    return conversation_instances

def get_conversations_from_elastic_search(community_id):
    """
    Get all conversations for a community from elastic search
    """

    # using scan get all hits from elastic search with community.id = community_id
    conversations = ConversationDocument.search().filter('term', community__id=community_id).scan()

    return conversations

def bulk_update_in_elastic_search_in_chunks(instances, chunk_size=1000):
    """
    Bulk update instances in chunks
    """

    # get total number of instances
    total_instances = instances.count()

    # get total number of chunks
    total_chunks = total_instances // chunk_size

    # if total instances are not divisible by chunk size then add one more chunk
    if total_instances % chunk_size != 0:
        total_chunks += 1

    # iterate over chunks
    for chunk in range(total_chunks):

        # get start and end index of chunk
        start_index = chunk * chunk_size
        end_index = start_index + chunk_size

        # get instances of chunk
        chunk_instances = instances[start_index:end_index]

        print(f'Starting bulk update in ES for chunk: {chunk} for community: {chunk_instances[0].community.id}')

        # bulk update chunk instances
        ConversationDocument().update(chunk_instances)

        if end_index > total_instances:
            end_index = total_instances

        print(f'Bulk update in ES Done: {end_index} done out of {total_instances}')


def reindex_missing_conversations_of_a_community(community_id):

    start_time = time.time()

    print(f'Reindexing missing conversations of community: {community_id}')

    # get card_answers instances of a community
    card_answers_instances = get_conversation_instances_of_a_community(community_id)
    card_answers_ids = card_answers_instances.values_list('id', flat=True)

    # get conversations from elastic search
    conversation_hits = get_conversations_from_elastic_search(community_id)
    conversation_hits_ids = [hit.id for hit in conversation_hits]

    # subtract conversations ids from card_answers ids
    missing_conversations_ids = list(set(card_answers_ids) - set(conversation_hits_ids))

    print(f'Total missing conversations: {len(missing_conversations_ids)}')

    # filter missing card_answers instances 
    missing_card_answers_instances = card_answers_instances.filter(id__in=missing_conversations_ids)

    # update missing conversations in Elastic Search
    bulk_update_in_elastic_search_in_chunks(missing_card_answers_instances, chunk_size=1000)

    end_time = time.time()

    print(f'({end_time - start_time} ms) Reindexing missing conversations of community: {community_id} completed')

# reindex all missing conversations of all SDK communities
def reindex_all_missing_conversations_of_all_sdk_communities():

    # get all SDK community ids
    community_ids = ModelUtilities.get_model_filter(SdkClient, {'is_deleted': False}).values_list('community_id', flat=True)
    
    total_communities = len(community_ids)
    print('Total communities: ', total_communities)

    # iterate over all community ids
    for community_id in community_ids:

        try:

            reindex_missing_conversations_of_a_community(community_id)

            total_communities -= 1

            print(f'Communities left to reindex: {total_communities}')
        
        except Exception as e:
            print(f'Error in reindexing community: {community_id}')
            print(e)

