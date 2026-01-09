import time
import traceback
import psycopg2

from django.core.paginator import Paginator

from togther.models import ModelUtilities, card_answers, collabcardState, Members
from collabmates_api.sdk.models import SdkClient
from collabmates_api.search.conversation_index import ConversationDocument
from collabmates_api.search.chatroom_index import ChatroomDocument
from collabmates_api.search.member_directory_index import MemberDirectoryDocument
from collabmates_api.notification import get_connection
from collabmates_api.raw_queries import get_tuple_from_array, error_logger


class DataHelper:

    @staticmethod
    def bulk_update_in_elastic_search(instances, chunk_size=1000):
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

            if isinstance(chunk_instances[0], Members):
                print(
                    f"Starting bulk update in ES for chunk: {chunk} for community: {chunk_instances[0].community_id.id}"
                )
            else:
                print(
                    f"Starting bulk update in ES for chunk: {chunk} for community: {chunk_instances[0].community.id}"
                )

            if isinstance(chunk_instances[0], collabcardState):
                ChatroomDocument().update(chunk_instances)
            elif isinstance(chunk_instances[0], card_answers):
                ConversationDocument().update(chunk_instances)
            elif isinstance(chunk_instances[0], Members):
                MemberDirectoryDocument().update(chunk_instances)

            if end_index > total_instances:
                end_index = total_instances

            print(f"Bulk update in ES Done: {end_index} done out of {total_instances}")

    @staticmethod
    def paginate_queryset(queryset, chunk_size):
        paginator = Paginator(queryset, chunk_size)
        for page_number in range(1, paginator.num_pages + 1):
            yield paginator.page(page_number).object_list


class ReindexBase:

    community_id = None
    db_chunk_size = 10000
    es_chunk_size = 5000

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
                # Print stack track
                traceback.print_exc()

    def get_missing_conversations_in_a_community(self, conversation_ids):
        if self.community_id is None:
            print("Community ID is None")
            return None

        conversation_instances = card_answers.objects.filter(
            community=self.community_id, is_deleted=False
        ).exclude(id__in=conversation_ids).order_by("id")

        return conversation_instances

    def get_conversation_ids_from_elastic_search(self):
        if self.community_id is None:
            print("Community ID is None")
            return None

        conversations = (
            ConversationDocument.search()
            .filter("term", community__id=self.community_id)
            .source(includes=["id"])
            .scan()
        )

        converstion_ids = [conversation.id for conversation in conversations]

        return converstion_ids

    @staticmethod
    def is_missing_chatrooms_exists_in_a_community(community_id: str = None, chatroom_ids: list = None):
        conn = get_connection()
        curr = conn.cursor()
        try:
            sql = f"""
                    SELECT COUNT(*)
                    FROM togther_collabcardState s
                    JOIN togther_collabcard c ON s.card_id = c.id
                    WHERE c.community_id = {community_id}
                      AND s.remove_id IS NULL
                      AND c.is_deleted = FALSE
                      AND s.secret_chatroom_left = FALSE
                      AND NOT EXISTS (
                          SELECT 1
                          FROM unnest(ARRAY[{','.join(chatroom_ids)}]::bigint[]) AS s(id)
                          WHERE t.id = s.id
                      );
                """

            print(sql)

            curr.execute(sql)
            card_tupple = curr.fetchone()
            curr.close()

            if card_tupple:
                return card_tupple[0] > 0

        except (Exception, psycopg2.Error) as error:
            error_logger.error("Error while connecting to PostgreSQL %s ", error)
            if conn:
                conn.close()

    def get_missing_chatrooms_in_a_community(self, chatroom_ids):
        if self.community_id is None:
            print("Community ID is None")
            return None

        chatrooms = collabcardState.objects.filter(
            community__id=self.community_id, remove=None
            ).exclude(card__is_deleted=True, secret_chatroom_left=True, id__in=chatroom_ids
            ).order_by("id"
            ).select_related("card", "community")

        return chatrooms

    def get_chatroom_ids_from_elastic_search(self):
        if self.community_id is None:
            print("Community ID is None")
            return None

        chatrooms = (
            ChatroomDocument.search()
            .filter("term", community__id=self.community_id)
            .source(includes=["id"])
            .scan()
        )

        chatroom_ids = [chatroom.id for chatroom in chatrooms]

        return chatroom_ids

    def get_missing_members_in_a_community(self, member_ids):
        if self.community_id is None:
            print("Community ID is None")
            return None

        return Members.objects.filter(community_id=self.community_id).exclude(
            id__in=member_ids).order_by("id").select_related("member_id", "community_id", "joined_by", "approved_by",
                                                             "parent_cm")

    def get_member_ids_from_elastic_search(self):
        if self.community_id is None:
            print("Community ID is None")
            return None

        members = (
            MemberDirectoryDocument.search()
            .filter("term", community_id__id=self.community_id)
            .source(includes=["id"])
            .scan()
        )

        return [member.id for member in members]


class ReindexChatrooms(ReindexBase):

    def reindex_missing_chatrooms_of_a_community(self):
        
        if self.community_id is None:
            print("Community ID is None")
            return None

        start_time = time.time()
        
        print(f"Reindexing missing chatrooms of community: {self.community_id}")

        chatroom_ids = self.get_chatroom_ids_from_elastic_search()
        chatroom_queryset = self.get_missing_chatrooms_in_a_community(chatroom_ids)

        if not self.is_missing_chatrooms_exists_in_a_community(
                community_id=self.community_id, chatroom_ids=chatroom_ids):
            return None
        
        print(f"Total missing chatrooms: {chatroom_queryset.count()}")
        
        for chatroom_instances in DataHelper.paginate_queryset(chatroom_queryset, self.db_chunk_size):

            DataHelper.bulk_update_in_elastic_search(
                chatroom_instances, chunk_size=self.es_chunk_size
            )
            
        self.print_time_taken(start_time, "Reindexing chatrooms")

    def reindex_chatrooms_for_all_communibulk_update_in_elastic_searchties(self):
        self.reindex_for_all_communities(self.reindex_missing_chatrooms_of_a_community)


class ReindexConversations(ReindexBase):

    def reindex_missing_conversations_of_a_community(self):
        
        if self.community_id is None:
            print("Community ID is None")
            return None

        start_time = time.time()
        print(f"Reindexing missing conversations of community: {self.community_id}")

        conversation_ids = self.get_conversation_ids_from_elastic_search()
        conversation_queryset = self.get_missing_conversations_in_a_community(conversation_ids)
        
        if not conversation_queryset.exists():
            return None
        
        print(f"Total missing conversations: {conversation_queryset.count()}")

        for converastion_instances in DataHelper.paginate_queryset(conversation_queryset, self.db_chunk_size):

            DataHelper.bulk_update_in_elastic_search(
                converastion_instances, chunk_size=self.es_chunk_size
            )
            
        self.print_time_taken(start_time, "Reindexed conversations")

    def reindex_conversations_for_all_communities(self):
        
        self.reindex_for_all_communities(
            self.reindex_missing_conversations_of_a_community
        )


class ReindexMembersDirectory(ReindexBase):

    def reindex_missing_members_of_a_community(self):

        if self.community_id is None:
            print("Community ID is None")
            return None

        start_time = time.time()
        print(f"Reindexing missing members of community: {self.community_id}")

        member_ids = self.get_member_ids_from_elastic_search()
        members_queryset = self.get_missing_members_in_a_community(member_ids)

        if not members_queryset.exists():
            return None

        print(f"Total missing members: {members_queryset.count()}")

        for members_instances in DataHelper.paginate_queryset(members_queryset, self.db_chunk_size):
            DataHelper.bulk_update_in_elastic_search(
                members_instances, chunk_size=self.es_chunk_size
            )

        self.print_time_taken(start_time, "Reindexed members")

    def reindex_members_for_all_communities(self):

        self.reindex_for_all_communities(
            self.reindex_missing_members_of_a_community()
        )


class ReindexManager:
    
    def __init__(self):
        self.chatroom_reindexer = ReindexChatrooms()
        self.conversation_reindexer = ReindexConversations()
        self.members_reindexer = ReindexMembersDirectory()

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

    def reindex_members_for_all_communities(self):
        self.members_reindexer.reindex_members_for_all_communities()

    def reindex_members_for_single_community(self, community_id):
        self.members_reindexer.community_id = community_id
        self.members_reindexer.reindex_missing_members_of_a_community()


def main():
    manager = ReindexManager()

    community_ids = []
    if not community_ids:
        print("Please provide a community ID list")
        exit()

    for community_id in community_ids:
        # Reindex members for a single community
        manager.reindex_members_for_single_community(community_id)

        # Reindex chatrooms for a single community
        manager.reindex_chatrooms_for_single_community(community_id)

        # Reindex conversations for a single community
        manager.reindex_conversations_for_single_community(community_id)

        # Reindex chatrooms for all active sdk communities
        # manager.reindex_chatrooms_for_all_communities()

        # Reindex conversations for all active sdk communities
        # manager.reindex_conversations_for_all_communities()


# Example usage
if __name__ == "__main__":
    main()
