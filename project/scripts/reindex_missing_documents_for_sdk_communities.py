import time

from togther.models import ModelUtilities, card_answers, collabcardState
from collabmates_api.sdk.models import SdkClient
from collabmates_api.search.conversation_index import ConversationDocument
from collabmates_api.search.chatroom_index import ChatroomDocument


class ElasticSearchHelper:

    @staticmethod
    def bulk_update_in_elastic_search_in_chunks(instances, chunk_size=1000):
        """
        Bulk update instances in chunks
        """
        total_instances = instances.count()
        total_chunks = total_instances // chunk_size

        if total_instances % chunk_size != 0:
            total_chunks += 1

        for chunk in range(total_chunks):
            start_index = chunk * chunk_size
            end_index = start_index + chunk_size
            chunk_instances = instances[start_index:end_index]
            
            if not chunk_instances:
                continue

            print(
                f"Starting bulk update in ES for chunk: {chunk} for community: {chunk_instances[0].community.id}"
            )
            
            if isinstance(chunk_instances[0], collabcardState):
                ChatroomDocument().update(chunk_instances)
            elif isinstance(chunk_instances[0], card_answers):
                ConversationDocument().update(chunk_instances)

            if end_index > total_instances:
                end_index = total_instances

            print(f"Bulk update in ES Done: {end_index} done out of {total_instances}")


class ReindexBase:
    
    community_id = None
    
    def __init__(self, community_id=None):
        self.community_id = community_id

    def print_time_taken(self, start_time, task_name):
        end_time = time.time()
        print(f"{task_name} took {end_time - start_time} seconds")

    def get_active_sdk_community_ids(self):
        return ModelUtilities.get_model_filter(
            SdkClient, {"is_deleted": False}
        ).values_list("community_id", flat=True)

    def reindex_for_all_communities(self, reindex_function):
        community_ids = self.get_active_sdk_community_ids()
        total_communities = len(community_ids)
        print("Total communities: ", total_communities)

        for community_id in community_ids:
            try:
                self.community_id = community_id
                reindex_function()
                total_communities -= 1
                print(f"Communities left to reindex: {total_communities}")
            except Exception as e:
                print(f"Error in reindexing community: {community_id}: {e}")

    def get_conversation_instances_of_a_community(self):
        if self.community_id is None:
            print("Community ID is None")
            return None

        conversation_instances = card_answers.objects.filter(
            community=self.community_id, is_deleted=False
        )
        return conversation_instances

    def get_conversations_from_elastic_search(self):
        if self.community_id is None:
            print("Community ID is None")
            return None

        conversations = (
            ConversationDocument.search()
            .filter("term", community__id=self.community_id)
            .scan()
        )
        return conversations

    def get_collabcard_states_instances_of_a_community(self):
        if self.community_id is None:
            print("Community ID is None")
            return None

        collabcard_states = (
            collabcardState.objects.filter(community__id=self.community_id, remove=None)
            .exclude(card__is_deleted=True, secret_chatroom_left=True)
            .select_related("card", "community")
        )

        return collabcard_states

    def get_chatrooms_from_elastic_search(self):
        if self.community_id is None:
            print("Community ID is None")
            return None

        chatrooms = (
            ChatroomDocument.search()
            .filter("term", community__id=self.community_id)
            .scan()
        )

        return chatrooms

class ReindexChatrooms(ReindexBase):

    def reindex_missing_chatrooms_of_a_community(self):
        
        if self.community_id is None:
            print("Community ID is None")
            return None

        start_time = time.time()
        print(f"Reindexing missing chatrooms of community: {self.community_id}")

        collabcard_states = self.get_collabcard_states_instances_of_a_community()
        collabcard_ids = collabcard_states.values_list("id", flat=True)

        chatroom_hits = self.get_chatrooms_from_elastic_search()
        chatroom_hits_ids = [hit.id for hit in chatroom_hits]

        missing_chatroom_ids = list(set(collabcard_ids) - set(chatroom_hits_ids))
        print(f"Total missing chatroom states: {len(missing_chatroom_ids)}")

        missing_chatroom_instances = collabcard_states.filter(
            id__in=missing_chatroom_ids
        )
        ElasticSearchHelper.bulk_update_in_elastic_search_in_chunks(
            missing_chatroom_instances, chunk_size=1000
        )

        self.print_time_taken(start_time, "Reindexing chatrooms")

    def reindex_chatrooms_for_all_communities(self):
        self.reindex_for_all_communities(self.reindex_missing_chatrooms_of_a_community)

class ReindexConversations(ReindexBase):
    
    def reindex_missing_conversations_of_a_community(self):
        if self.community_id is None:
            print("Community ID is None")
            return None

        start_time = time.time()
        print(f"Reindexing missing conversations of community: {self.community_id}")

        card_answers_instances = self.get_conversation_instances_of_a_community()
        card_answers_ids = card_answers_instances.values_list("id", flat=True)

        conversation_hits = self.get_conversations_from_elastic_search()
        conversation_hits_ids = [hit.id for hit in conversation_hits]

        missing_conversations_ids = list(
            set(card_answers_ids) - set(conversation_hits_ids)
        )
        print(f"Total missing conversations: {len(missing_conversations_ids)}")

        missing_card_answers_instances = card_answers_instances.filter(
            id__in=missing_conversations_ids
        )
        ElasticSearchHelper.bulk_update_in_elastic_search_in_chunks(
            missing_card_answers_instances, chunk_size=1000
        )

        self.print_time_taken(start_time, "Reindexing conversations")

    def reindex_conversations_for_all_communities(self):
        self.reindex_for_all_communities(
            self.reindex_missing_conversations_of_a_community
        )

class ReindexManager:
    
    def __init__(self):
        self.chatroom_reindexer = ReindexChatrooms()
        self.conversation_reindexer = ReindexConversations()

    def reindex_chatrooms_for_all_communities(self):
        self.chatroom_reindexer.reindex_chatrooms_for_all_communities()

    def reindex_chatrooms_for_single_community(self, community_id):
        self.chatroom_reindexer.community_id = community_id
        self.chatroom_reindexer.reindex_missing_chatrooms_of_a_community()

    def reindex_conversations_for_all_communities(self):
        self.conversation_reindexer.reindex_conversations_for_all_communities()

    def reindex_conversations_for_single_community(self, community_id):
        self.conversation_reindexer.community_id = community_id
        self.conversation_reindexer.reindex_missing_conversations_of_a_community()


# Example usage
if __name__ == "__main__":
    manager = ReindexManager()

    community_id = None
    if community_id is None:
        print("Please provide a community ID")
        exit()

    # Reindex chatrooms for a single community
    manager.reindex_chatrooms_for_single_community(community_id)

    # Reindex conversations for a single community
    manager.reindex_conversations_for_single_community(community_id)

    # Reindex chatrooms for all active sdk communities
    # manager.reindex_chatrooms_for_all_communities()

    # Reindex conversations for all active sdk communities
    # manager.reindex_conversations_for_all_communities()
