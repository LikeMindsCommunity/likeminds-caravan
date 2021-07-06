from typing import Union
from elasticsearch_dsl import Search
from .search_manager import SearchManager
from .search_helper import SearchHelper
from togther.models import collabcardState, userMemberRights, Members

from utility.states import member_rights, card_types, member_states
from utility.number_utilities import NumberUtilities


class SearchImpl(SearchManager):

    def __init__(self, member_id: str, search_term: str, search_field: str = None,
                 follow_status: bool = False, page: int = 1, page_size: int = 300,
                 device_id: str = None):
        self.member_id = member_id
        self.search_term = search_term
        self.search_field = search_field
        self.follow_status = follow_status
        self.page = page
        self.page_size = page_size
        self.device_id = device_id

    def get_member_id(self) -> Union[str, int]:
        return self.member_id

    def set_member_id(self, member_id: Union[str, int]) -> None:
        self.member_id = member_id

    def get_search_term(self) -> str:
        return self.search_term.lower()

    def get_search_field(self) -> str:
        return self.search_field.lower()

    def get_follow_status(self) -> bool:
        return self.follow_status

    def get_page_number(self) -> int:
        return self.page

    def get_page_size(self) -> int:
        return self.page_size

    def _get_chatroom_search_query_dict(self):
        """
        @return: dict
        """
        return {
            "from": self.get_page_size()*(self.get_page_number()-1),
            "size": self.get_page_size(),
            "sort": {
                "_score": {
                    "order": "desc"
                },
                "updated_at": {
                    "order": "desc"
                },
                "_score": {
                    "order": "desc"
                }
            },
            "query": {
                "bool": {
                    "must": [{
                        "query_string": {
                            "query": f"*{self.get_search_term()}*",
                            "fields": [
                                f"chatroom.{self.get_search_field()}"
                            ]
                        }
                    }
                    ],
                    "filter": [
                        {"term": {"member.id": f"{self.get_member_id()}"}},
                        {"term": {"follow_status": self.get_follow_status()}}
                    ]
                }
            }
        }

    def _get_chatroom_search_ngram_query_dict(self):
        """
        @return: dict
        """
        return {
            "from": self.get_page_size()*(self.get_page_number()-1),
            "size": self.get_page_size(),
            "sort": {
                "_score": {
                    "order": "desc"
                },
                "updated_at": {
                    "order": "desc"
                }
            },
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {"member.id": self.get_member_id()}
                        },
                        {
                            "term": {"follow_status": self.get_follow_status()}
                        },
                        {
                            "bool": {
                                "should": [
                                    {
                                        "match": {
                                            f"chatroom.{self.get_search_field()}": {
                                                "query": self.get_search_term(),
                                                "analyzer": "standard"
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }

    def _get_conversation_search_query_dict(self, chatroom_id_list):
        return {
            "from": self.get_page_size()*(self.get_page_number()-1),
            "size": self.get_page_size(),
            "sort": {
                "_score": {
                    "order": "desc"
                },
                "last_updated": {
                    "order": "desc"
                }
            },
            "query": {
                "bool": {
                    "must": [{
                        "query_string": {
                            "query": f"*{self.get_search_term()}*",
                            "fields": [
                                "answer"
                            ]
                        }
                    }
                    ],
                    "filter": [
                        {
                            "terms": {
                                "chatroom.id": chatroom_id_list
                            }
                        }
                    ]
                }
            }
        }

    def _get_conversation_search_ngram_query_dict(self, chatroom_id_list):

        return {
            "from": self.get_page_size()*(self.get_page_number()-1),
            "size": self.get_page_size(),
            "sort": {
                "_score": {
                    "order": "desc"
                },
                "last_updated": {
                    "order": "desc"
                }
            },
            "query": {
                "bool": {
                    "must": [
                        {
                            "terms": {"chatroom.id": chatroom_id_list}
                        },
                        {
                            "bool": {
                                "should": [
                                    {
                                        "match": {
                                            "answer": {
                                                "query": f"{self.get_search_term()}",
                                                "analyzer": "standard"
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }

    def _fetch_user_chatrooms_id_list(self):
        return list(collabcardState.objects
                    .filter(user__id=self.get_member_id(),
                            card__is_deleted=False,
                            secret_chatroom_left=False,
                            follow_status=self.get_follow_status(),
                            remove=None)
                    .values_list('card_id', flat=True))

    def _fetch_user_community_id_list_with_respond_right(self):

        community_ids = list(userMemberRights.objects
                            .filter(user__id=self.get_member_id(),
                                    right__state=member_rights.MEMBER_RIGHT_RESPOND_IN_ROOM)
                            .values_list("community_id", flat=True))

        return community_ids

    def _fetch_user_community_id_list_as_manager(self):

        community_ids = list(Members.objects
                             .filter(member_id__id=self.get_member_id(),
                                     state=member_states.ADMIN)
                             .values_list("community_id", flat=True))

        return community_ids

    def _fetch_hash_for_community_id(self, respond_right_community_id_list):

        return {community_id: True for community_id in respond_right_community_id_list}

    def _should_disable_chatroom(self, chatroom, right_community_id_hash, community_manager_id_hash):
        is_disabled = False

        if (chatroom['chatroom']['type'] == card_types.CARD_PURPOSE and
            not community_manager_id_hash.get(chatroom['community']['id'], False)) or \
                chatroom['chatroom']['type'] == card_types.CARD_MASTER_INTRO or \
                chatroom['chatroom']['is_pending'] or \
                not right_community_id_hash.get(chatroom['community']['id'], False) or \
                not SearchHelper.has_attachments_uploaded(chatroom['chatroom']):

            is_disabled = True

        return is_disabled

    def search_chatroom(self):

        res = Search.from_dict(self._get_chatroom_search_ngram_query_dict()).execute()

        context = {
            'chatrooms': [hit.to_dict() for hit in res]
        }

        return context

    def search_conversation(self):

        chatroom_id_list = self._fetch_user_chatrooms_id_list()

        res = Search.from_dict(self._get_conversation_search_ngram_query_dict(chatroom_id_list)).execute()

        context = {
            'conversations': [hit.to_dict() for hit in res]
        }

        return context

    def search_third_party(self):

        chatroom_data = self.search_chatroom()

        respond_right_community_id_list = self._fetch_user_community_id_list_with_respond_right()

        community_ids_as_manager = self._fetch_user_community_id_list_as_manager()

        community_manager_id_hash = self._fetch_hash_for_community_id(community_ids_as_manager)
        right_community_id_hash = self._fetch_hash_for_community_id(respond_right_community_id_list)

        for chatroom in chatroom_data['chatrooms']:
            chatroom['is_disabled'] = self._should_disable_chatroom(chatroom,
                                                                    right_community_id_hash,
                                                                    community_manager_id_hash)

        return chatroom_data
