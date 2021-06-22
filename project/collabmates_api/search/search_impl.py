from typing import Union
from elasticsearch_dsl import Search
from .search_manager import SearchManager
from togther.models import collabcardState


class SearchImpl(SearchManager):

    def __init__(self, member_id: str, search_term: str, search_field: str = None,
                 follow_status: bool = False, page: int = 1, page_size: int = 300):
        self.member_id = member_id
        self.search_term = search_term
        self.search_field = search_field
        self.follow_status = follow_status
        self.page = page
        self.page_size = page_size

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
                "updated_at": {
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
