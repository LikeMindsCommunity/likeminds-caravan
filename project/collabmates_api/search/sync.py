from elasticsearch_dsl import Search, UpdateByQuery
from elasticsearch import Elasticsearch

from celery import shared_task
from utility.states import SearchIndexes, conversation_states

from togther.models import collabcardState, card_answers

from django_elasticsearch_dsl.registries import registry

client = Elasticsearch()


class ElasticSearchSync:
    
    @staticmethod
    def bulk_update_documents(index: SearchIndexes, query_dict: dict):
        """
        @param index: enum SearchIndexes
        @param query_dict: dict
        @return: None
        @description: bulk updates all documents with matching condition
        """
        s = UpdateByQuery(index=index.value).update_from_dict(query_dict)
        s.execute()

    @staticmethod
    def delete_documents(index: SearchIndexes, query_dict: dict):
        """
        @param index: enum SearchIndexes
        @param query_dict: dict
        @return: None
        @description: delete documents from elastic search permanently
        """
        s = Search(index=index.value).update_from_dict(query_dict)
        s.delete()

    @staticmethod
    def update_document(instance_list: list):
        """
        @param instance_list: list of instances
        @return: None
        @description: updates documents in elastics search
        """
        for instance in instance_list:
            registry.update(instance)

    @staticmethod
    @shared_task
    def update_chatroom_for_user(chatroom_id: int, user_id: int):
        """
        @param chatroom_id: int
        @param user_id: int
        @return: None
        @description: updates all chatrooms for a single user
        """
        instances = collabcardState.objects \
            .filter(card__id=chatroom_id, user__id=user_id, remove=None) \
            .exclude(card__is_deleted=True, secret_chatroom_left=True) \
            .select_related('card', 'community')

        ElasticSearchSync.update_document(instances)

    @staticmethod
    @shared_task
    def update_chatroom(chatroom_id: int):
        """
        @param chatroom_id: int
        @return: None
        @description: updates a single chatroom related content
        """

        instances = collabcardState.objects \
            .filter(card__id=chatroom_id, remove=None) \
            .exclude(card__is_deleted=True, secret_chatroom_left=True) \
            .select_related('card', 'community')

        ElasticSearchSync.update_document(instances)

    @staticmethod
    @shared_task
    def update_all_community_chatrooms(community_id: int):
        """
        @param community_id: int
        @return: None
        @description: updates all chatrooms in a given community
        """
        instances = collabcardState.objects \
            .filter(community__id=community_id, remove=None) \
            .exclude(card__is_deleted=True, secret_chatroom_left=True) \
            .select_related('card', 'community')

        ElasticSearchSync.update_document(instances)

    @staticmethod
    @shared_task
    def delete_chatrooms_for_removed_member(community_id: int, user_id: int):
        """
        @param community_id: int
        @param user_id: int
        @return: None
        @description: updates all chatrooms and conversation in a community for removed member
        """

        query_dict = ElasticSearchQueryHelper.get_delete_dict_for_removed_member(community_id, user_id)
        ElasticSearchSync.delete_documents(index=SearchIndexes.CHATROOM,
                                           query_dict=query_dict)
        ElasticSearchSync.delete_all_community_conversations(community_id)

    @staticmethod
    @shared_task
    def update_chatrooms_for_rejoined_member(community_id: int, user_id: int):
        """
        @param community_id: int
        @param user_id: int
        @return: None
        @description: updates all chatrooms in a community for rejoined member
        """
        instances = collabcardState.objects \
            .filter(community__id=community_id, user__id=user_id, remove=None) \
            .exclude(card__is_deleted=True, secret_chatroom_left=True) \
            .select_related('card', 'community')

        ElasticSearchSync.update_document(instances)

    @staticmethod
    @shared_task
    def delete_chatroom(chatroom_id: int):
        """
        @param chatroom_id: int
        @return: None
        @description: Delete a chatroom and its related conversations
        """

        query_dict = ElasticSearchQueryHelper.get_all_chatroom_dict(chatroom_id)
        ElasticSearchSync.delete_documents(index=SearchIndexes.CHATROOM,
                                           query_dict=query_dict)
        ElasticSearchSync.delete_chatroom_conversations(chatroom_id)

    @staticmethod
    @shared_task
    def delete_chatroom_conversations(chatroom_id: int):
        """
        @param chatroom_id: int
        @return: None
        @description: Delete all conversations of a chatroom
        """

        query_dict = ElasticSearchQueryHelper.get_all_chatroom_dict(chatroom_id)
        ElasticSearchSync.delete_documents(index=SearchIndexes.CONVERSATION,
                                           query_dict=query_dict)

    @staticmethod
    @shared_task
    def delete_all_community_conversations(community_id: int):
        """
        @param community_id: int
        @return: None
        @description: Delete one or more conversations
        """

        query_dict = ElasticSearchQueryHelper.get_community_dict(community_id)
        ElasticSearchSync.delete_documents(index=SearchIndexes.CONVERSATION,
                                           query_dict=query_dict)

    @staticmethod
    @shared_task
    def delete_conversations(conversation_id_list: list):
        """
        @param conversation_id_list: list
        @return: None
        @description: Delete one or more conversations
        """

        query_dict = ElasticSearchQueryHelper.get_conversations_by_ids(conversation_id_list)
        ElasticSearchSync.delete_documents(index=SearchIndexes.CONVERSATION,
                                           query_dict=query_dict)

    @staticmethod
    @shared_task
    def update_all_conversations_of_community(community_id: int):
        """
        @param community_id: int
        @return: None
        @description: Updates all conversations full models of communities
        """
        instances = card_answers.objects \
            .filter(community__id=community_id, remove=None,
                    state__in=[conversation_states.ANSWER, conversation_states.CONVERSATION_POLL]) \
            .exclude(card__is_deleted=True) \
            .select_related('card', 'community')

        ElasticSearchSync.update_document(instances)

    @staticmethod
    @shared_task
    def update_all_conversations_of_chatroom(chatroom_id: int):
        """
        @param chatroom_id: int
        @return: None
        @description: Updates all conversations full models of a chatroom
        """
        instances = card_answers.objects \
            .filter(card__id=chatroom_id, remove=None,
                    state__in=[conversation_states.ANSWER, conversation_states.CONVERSATION_POLL]) \
            .exclude(card__is_deleted=True) \
            .select_related('card', 'community')

        ElasticSearchSync.update_document(instances)

    @staticmethod
    @shared_task
    def update_conversations(conversation_ids: list):
        """
        @param conversation_ids: list<int>
        @return: None
        @description: Updates all conversations full models for given conversation ids
        """
        instances = card_answers.objects \
            .filter(id__in=conversation_ids, remove=None,
                    state__in=[conversation_states.ANSWER, conversation_states.CONVERSATION_POLL]) \
            .exclude(card__is_deleted=True) \
            .select_related('card', 'community')

        ElasticSearchSync.update_document(instances)

    @staticmethod
    @shared_task
    def update_all_conversations_of_user(user_id: int):
        """
        @param user_id: int
        @return: None
        @description: Updates all conversations full models created by a user
        """
        instances = card_answers.objects \
            .filter(user__id=user_id, remove=None,
                    state__in=[conversation_states.ANSWER, conversation_states.CONVERSATION_POLL]) \
            .exclude(card__is_deleted=True) \
            .select_related('card', 'community')

        ElasticSearchSync.update_document(instances)

    @staticmethod
    @shared_task
    def update_chatroom_name(chatroom_id: int, chatroom_name: str):
        """
        @param chatroom_id: int
        @param chatroom_name: str
        @return: None
        @description: Bulk updates chatroom name in conversations related to renamed chatroom
        """
        query_dict = ElasticSearchQueryHelper.get_chatroom_rename_update_dict(chatroom_id, chatroom_name)
        ElasticSearchSync.bulk_update_documents(index=SearchIndexes.CHATROOM,
                                                query_dict=query_dict)
        ElasticSearchSync.bulk_update_documents(index=SearchIndexes.CONVERSATION,
                                                query_dict=query_dict)

    @staticmethod
    @shared_task
    def update_community_name(community_id: int, community_name: str):
        """
        @param community_id: int
        @param community_name: str
        @return: None
        @description: Bulk updates community name in conversations and chatrooms related to renamed community
        """
        query_dict = ElasticSearchQueryHelper.get_community_rename_update_dict(community_id, community_name)
        ElasticSearchSync.bulk_update_documents(index=SearchIndexes.CHATROOM,
                                                query_dict=query_dict)
        ElasticSearchSync.bulk_update_documents(index=SearchIndexes.CONVERSATION,
                                                query_dict=query_dict)

    @staticmethod
    @shared_task
    def update_user_name(user_id: int, user_name: str):
        """
        @param user_id: int
        @param user_name: str
        @return: None
        @description: Bulk updates user name in conversations and chatrooms created by the user
        """
        query_dict = ElasticSearchQueryHelper.get_user_rename_update_dict(user_id, user_name)
        ElasticSearchSync.bulk_update_documents(index=SearchIndexes.CONVERSATION,
                                                query_dict=query_dict)


class ElasticSearchQueryHelper:
    @staticmethod
    def get_all_chatroom_dict(chatroom_id: int):
        """
        @param chatroom_id: int
        @return: dict
        @sql: where chatroom_id = chatroom_id
        """
        return {
            "query": {
                "match": {
                    "chatroom.id": chatroom_id
                }
            }
        }

    @staticmethod
    def get_delete_dict_for_removed_member(community_id: int, user_id: int):
        """
        @param community_id: int
        @param user_id: int
        @return: dict
        @sql: where community_id = community_id and member_id = user_id
        """
        return {
            "query": {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "community.id": community_id
                            }
                        }
                    ],
                    "filter": [
                        {
                            "term": {
                                "member.id": user_id
                            }
                        }
                    ]
                }
            }
        }

    @staticmethod
    def get_update_chatroom_dict(chatroom_id: int):
        """
        @param chatroom_id: int
        @return: dict
        @sql: where chatroom_id = chatroom_id
        """
        return {
            "query": {
                "match": {
                    "chatroom.id": chatroom_id
                }
            }
        }

    @staticmethod
    def get_conversations_by_ids(conversation_id_list: list):
        """
        @param conversation_id_list: list<int>
        @return: dict
        @sql: where id in (list of ids)
        """
        return {
            "query": {
                "terms": {
                    "_id": conversation_id_list
                }
            }
        }

    @staticmethod
    def get_community_dict(community_id: int):
        """
        @param community_id: int
        @return: dict
        @sql: where community_id = community_id
        """
        return {
            "query": {
                "match": {
                    "community.id": community_id
                }
            }
        }

    @staticmethod
    def get_chatroom_rename_update_dict(chatroom_id: int, header: str):
        """
        @param chatroom_id: int
        @param header: str
        @return: dict
        @sql: update set chatroom_header = header where chatroom_id = chatroom_id
        """
        return {
            "script": {
                "inline": f"ctx._source.chatroom.header = '{header}'",
                "lang": "painless"
            },
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "chatroom.id": {
                                    "value": chatroom_id
                                }
                            }
                        }
                    ]
                }
            }
        }

    @staticmethod
    def get_community_rename_update_dict(community_id: int, community_name: str):
        """
        @param community_id: int
        @param community_name: str
        @return: dict
        @sql: update set community_name = community_name where community_id = community_id
        """
        return {
            "script": {
                "inline": f"ctx._source.community.name = '{community_name}'",
                "lang": "painless"
            },
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "community.id": {
                                    "value": community_id
                                }
                            }
                        }
                    ]
                }
            }
        }

    @staticmethod
    def get_user_rename_update_dict(user_id: int, user_name: str):
        """
        @param user_id: int
        @param user_name: str
        @return: dict
        @sql: update set member_profile_name = user_name where member_id = user_id
        """
        return {
            "script": {
                "inline": f"ctx._source.member.profile.name = '{user_name}'",
                "lang": "painless"
            },
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "member.id": {
                                    "value": user_id
                                }
                            }
                        }
                    ]
                }
            }
        }
