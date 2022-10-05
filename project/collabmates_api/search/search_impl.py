from typing import Union
from elasticsearch_dsl import Search
from .search_manager import SearchManager
from .search_helper import SearchHelper
from togther.models import collabcardState, userMemberRights, Members, communityAnswers, ModelUtilities

from utility.states import member_rights, card_types, member_states, question_states
from utility.number_utilities import NumberUtilities
from utility.time_utilities import TimeUtilities
from .constants import CUSTOM_INTRO_TEXT_FOR_ADMIN, CUSTOM_INTRO_TEXT_FOR_MEMBERS, CUSTOM_CLICK_TEXT_FOR_MEMBERS
from .constants import MEMBER_DIRECTORY_INDEX_FIELDS_DICTIONARY_MAPPING


class SearchImpl(SearchManager):

    def __init__(self, member_id: str, search_term: str, search_field: str = None,
                 follow_status: bool = False, page: int = 1, page_size: int = 300,
                 device_id: str = None, community_id: str = None):
        self.member_id = member_id
        self.search_term = search_term
        self.search_field = search_field
        self.follow_status = follow_status
        self.page = page
        self.page_size = page_size
        self.device_id = device_id
        self.community_id = community_id

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

    def get_community_id(self) -> Union[str, int]:
        return NumberUtilities.get_integer_from_string(self.community_id)

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
                    ],
                    "must_not": [
                        {
                            "term": {"chatroom.type": card_types.CARD_DIRECT_MESSAGE}
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
    
    def _get_member_directory_search_ngram_query_dict(self, search_field):
        """
        @param search_field: Field of member index
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
                            "term": {"community_id.id": self.get_community_id()}
                        },
                        {
                            "bool": {
                                "should": [
                                    {
                                        "match": {
                                            MEMBER_DIRECTORY_INDEX_FIELDS_DICTIONARY_MAPPING[search_field]: {
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

    def _fetch_user_chatrooms_id_list(self, community_id: int) -> list:
        filter_dict = {
            'user__id': self.get_member_id(),
            'card__is_deleted': False,
            'card__is_private': False,
            'secret_chatroom_left': False,
            'follow_status': self.get_follow_status(),
            'remove': None
        }

        if community_id:
            filter_dict['community_id'] = community_id

        return list(collabcardState.objects
                    .filter(**filter_dict)
                    .values_list('card_id', flat=True))

    def _fetch_user_community_id_list_with_respond_right(self):

        community_ids = list(userMemberRights.objects.filter(user__id=self.get_member_id(),
                                                             right__state=member_rights.MEMBER_RIGHT_RESPOND_IN_ROOM).
                             values_list("community_id", flat=True))

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

    def search_chatroom(self, community_id: int):

        search_query_dict = self._get_chatroom_search_ngram_query_dict()

        if community_id:
            self._append_community_id(search_query_dict, community_id)

        res = Search.from_dict(search_query_dict).execute()

        context = {
            'success': True,
            'chatrooms': [hit.to_dict() for hit in res]
        }

        return context

    @staticmethod
    def _append_community_id(search_query_dict: dict, community_id: int) -> None:
        community_id_param_dict = {
            "term": {
                "community.id": community_id
            }
        }

        must_params_dict = search_query_dict['query']['bool']['must']
        must_params_dict.append(community_id_param_dict)

    def search_conversation(self, community_id: int):

        chatroom_id_list = self._fetch_user_chatrooms_id_list(community_id)

        res = Search.from_dict(self._get_conversation_search_ngram_query_dict(chatroom_id_list)).execute()

        context = {
            'success': True,
            'conversations': [hit.to_dict() for hit in res]
        }

        return context

    def search_third_party(self, community_id: int):

        chatroom_data = self.search_chatroom(community_id)

        respond_right_community_id_list = self._fetch_user_community_id_list_with_respond_right()

        community_ids_as_manager = self._fetch_user_community_id_list_as_manager()

        community_manager_id_hash = self._fetch_hash_for_community_id(community_ids_as_manager)
        right_community_id_hash = self._fetch_hash_for_community_id(respond_right_community_id_list)

        for chatroom in chatroom_data['chatrooms']:
            chatroom['is_disabled'] = self._should_disable_chatroom(chatroom,
                                                                    right_community_id_hash,
                                                                    community_manager_id_hash)

        return chatroom_data

    @staticmethod
    def get_custom_click_intro_text(member_name, state, created_at):
        custom_intro_text, custom_click_text = None, None

        if state == member_states.ADMIN:
            custom_intro_text = CUSTOM_INTRO_TEXT_FOR_ADMIN % \
                                TimeUtilities.convert_epoch_time_in_date(
                                    created_at)

        if state in [member_states.MEMBER, member_states.PROFILE_UNAVAILABLE]:
            custom_intro_text = CUSTOM_INTRO_TEXT_FOR_MEMBERS % (
                TimeUtilities.convert_epoch_time_in_date(created_at))

            custom_click_text = CUSTOM_CLICK_TEXT_FOR_MEMBERS % (
                member_name,
                TimeUtilities.convert_epoch_time_in_date(created_at))

        return custom_intro_text, custom_click_text

    @staticmethod
    def get_image_url(member_img_url, user_img_url):
        member_img = None

        if member_img_url is not None:
            member_img = member_img_url
        else:
            if user_img_url['image_link']:
                member_img = user_img_url['image_link']

            else:
                member_img = user_img_url['image_url']

        return member_img

    def search_member_directory(self):

        res = Search.from_dict(self._get_member_directory_search_ngram_query_dict(
            self.get_search_field())).execute()

        members_list = []

        user_list = [hit['member']['id'] for hit in res]

        introduction_filter = ModelUtilities.get_model_filter(communityAnswers,
                                                              {'question__question_state': question_states.INTRODUCTION,
                                                               'question__community__id': self.get_community_id(),
                                                               'member__id__in': user_list})

        answer_dict = {instance.member_id: instance for instance in introduction_filter}

        for hit in res:
            member_introduction_dict = dict()

            if hit['member']['id'] in answer_dict:
                answer_instance = answer_dict[hit['member']['id']]

                member_dict = dict()
                member_dict['member_id'] = hit['member']['id']
                member_dict['community_id'] = self.get_community_id()
                member_dict['state'] = answer_instance.question.question_state
                member_dict['value'] = answer_instance.question_answer
                member_dict['question_id'] = answer_instance.question.id
                member_dict['is_hidden'] = answer_instance.question.is_hidden
                member_dict['directory_fields'] = answer_instance.question.field
                member_dict['question_title'] = answer_instance.question_title
                member_introduction_dict['question_answers'] = [member_dict]

            else:
                custom_intro_text, custom_click_text = self.get_custom_click_intro_text(hit['member']['user'][
                                                                                            'name'], hit['state'],
                                                                                        hit['created_at'])

                if custom_intro_text is not None:
                    member_introduction_dict['custom_intro_text'] = custom_intro_text

                if custom_click_text is not None:
                    member_introduction_dict['custom_click_text'] = custom_click_text

            member_introduction_dict['id'] = hit['member']['id']
            member_introduction_dict['name'] = hit['member']['user']['name']
            member_introduction_dict['updated_at'] = hit['updated_at']
            member_introduction_dict['member_cohorts'] = [cohort.to_dict() for cohort in hit['cohorts']]

            member_img = self.get_image_url(hit['image_url'], hit['member']['user'])

            if member_img is not None:
                member_introduction_dict['image_url'] = member_img

            member_introduction_dict['state'] = hit['state']
            member_introduction_dict['is_owner'] = hit['is_owner']

            if hit['custom_title'] and not hit['custom_title'] == 'Member':
                member_introduction_dict['custom_title'] = hit['custom_title']

            members_list.append(member_introduction_dict)

        context = {
            'members': members_list
        }

        return context
