import traceback
from typing import List

from ..models.message import MessageModel, ReactionModel, PollOptionsModel
from ..models.user import Users
from ..constants import SENDBIRD_MESSAGE_MAP_KEY
from ..constants import TTL_FOR_CACHE
from ..utils.sendbird_utils import SendbirdApiUtils
from ..utils.migration_utils import MigrationUtils

from togther.models import ModelUtilities, card_answers, conversationPolls, answerAttachment
from collabmates_api.conversation.conversation_impl import ConversationImpl
from utility.version_utilities import VersionUtilities
from external_services.caching.cache_impl import CacheImpl

from external_services.logging.logging_wrapper import LoggingWrapper

info_logger = LoggingWrapper.get_instance()
error_logger = LoggingWrapper.get_instance()

class MigrateMessages:

    api_key: str = ""
    platform_code: str = ""
    version_code: str = ""
    community_id: int = None
    sendbird_api_utils: SendbirdApiUtils = None

    messages_data = []

    def __init__(self, api_key: str, community_id: int, platform_code: str, version_code: str, 
                 messages_data: List[MessageModel], sendbird_api_utils: SendbirdApiUtils = None):

        self.api_key = api_key
        self.community_id = community_id
        self.platform_code = platform_code
        self.version_code = version_code
        self.messages_data = messages_data

        if sendbird_api_utils:
            self.sendbird_api_utils = sendbird_api_utils

    def _create_conversation(self, user_id: int, platform_code: str, version_code: str, req_body: dict,
                             created_at: int, is_deleted: bool):

        conversation_manager = ConversationImpl(
            member_id=user_id,
            platform_code=platform_code,
            version_code=version_code,
            api_version_code=VersionUtilities.APIVersionCodes.V1.value
        )

        # Create Message
        conversation_response = conversation_manager.create_conversation_v1(req_body, internal_migration=True)
        if conversation_response.get("error_message"):
            raise ValueError(f"Error in create_conversation_v1: {conversation_response.get('error_message')} | "
                             f"req_body: {req_body} | user_id: {user_id}")

        conversation_id = conversation_response.get("id")
        if not conversation_id:
            raise ValueError(f"Cannot find conversation_id in response for user_id: {user_id} | "
                             f"conversation_response: {conversation_response}")

        # Update conversation created_at and is_deleted
        filter_dict = {
            "id": conversation_id
        }

        update_dict = {
            "last_updated": created_at,
            "created_at": created_at,
        }

        if is_deleted:
            update_dict["is_deleted"] = True
            update_dict["deleted_by_user_id"] = user_id

        ModelUtilities.model_update(card_answers, filter_dict, update_dict)

        # Update conversationPolls created_at
        polls = conversation_response.get("conversation", {}).get("polls")
        if polls:
            filter_dict = {
                "conversation_id": conversation_id
            }

            update_dict = {
                "created_at": created_at,
                "updated_at": created_at
            }

            ModelUtilities.model_update(conversationPolls, filter_dict, update_dict)

        # Update answerAttachment created_at
        attachments = conversation_response.get("conversation", {}).get("attachments")
        if attachments:
            filter_dict = {
                'answer_id': conversation_id,
            }

            update_dict = {
                "created_at": created_at,
            }

            ModelUtilities.model_update(answerAttachment, filter_dict, update_dict)

        return conversation_response

    @staticmethod
    def _create_reactions_for_message(reactions: List[ReactionModel], conversation_id: int, chatroom_id: int):

        for reaction in reactions:
            for reaction_user_id in reaction.user_ids:
                conversation_manager = ConversationImpl(
                    member_id=reaction_user_id,
                    chatroom_id=chatroom_id,
                    conversation_id=conversation_id,
                )

                reaction_response = conversation_manager.add_reaction(reaction.reaction_key)
                if reaction_response.get("error_message"):
                    info_logger.error(
                        (
                            f"SendbirdMigration | Error in add_reaction: {reaction_response.get('error_message')} | "
                            f"user_id: {reaction_user_id} | reaction: {reaction} | conversation_id: {conversation_id} | "
                            f"chatroom_id: {chatroom_id}"
                        )
                    )
                    raise ValueError(reaction_response.get("error_message"))

        return 

    def _create_poll_votes(self, conversation_id: int, conversation_polls: List[dict], sendbird_polls: List[PollOptionsModel], ):

        if not (conversation_id or conversation_polls or sendbird_polls):
            return

        if len(conversation_polls) != len(sendbird_polls):
            info_logger.error(
                (
                    f"SendbirdMigration | Conversation Polls and Sendbird Polls length mismatch for conversation_id: {conversation_id}"
                )
            )
            return

        for index, sendbird_poll in enumerate(sendbird_polls):
            option_id = sendbird_poll.id
            poll_id = sendbird_poll.poll_id

            # Fetch Poll voters for each option
            for voters in self.sendbird_api_utils.yield_poll_voters_for_option(poll_id, option_id):

                # Load up the users and validate them
                users = Users(users=voters).users

                # For each user, submit poll
                for user in users:

                    # Fetch LM user_id
                    lm_user_id = MigrationUtils.get_lm_user_id_from_sendbird_user_id(user.uuid, self.community_id)
                    if not lm_user_id:
                        info_logger.error(
                            (
                                f"SendbirdMigration | In _create_poll_votes LM user_id not found for sendbird_user_id: {user.uuid}"
                            )
                        )
                        continue

                    req_body = {
                        "conversation_id": conversation_id,
                        "polls": [{"id": conversation_polls[index].get("id")}]
                    }

                    # Submit Poll
                    response = ConversationImpl(member_id=lm_user_id).submit_poll(req_body)
                    if response.get("error_message"):
                        info_logger.error(
                            (
                                f"SendbirdMigration | Error in submit_poll: {response.get('error_message')} |" 
                                f"lm_user_id: {lm_user_id} | conversation_id: {conversation_id} | poll_id: {poll_id} "
                                f"| option_id: {option_id}"
                            )
                        )
                    else:
                        info_logger.info(
                            (
                                f"SendbirdMigration | Poll submitted for lm_user_id: {lm_user_id} " 
                                f"| conversation_id: {conversation_id} | poll_id: {poll_id} | option_id: {option_id}"
                            )
                        )

        return

    def _create_conversation_and_its_related_data(self, sendbird_message_id: str,  user_id: int, community_id: int,
                                                  req_body: dict, chatroom_id: int, created_at: int, is_deleted: bool,
                                                  reactions: List[ReactionModel] = None, 
                                                  poll_options: List[PollOptionsModel] = None):

        conversation_id = CacheImpl.get_cache(SENDBIRD_MESSAGE_MAP_KEY.format(community_id, sendbird_message_id))
        if conversation_id:
            info_logger.info(
                            f"SendbirdMigration | Conversation already created for sendbird_message_id: {sendbird_message_id}"
                        )
            return
        else:

            info_logger.info(
                (
                    f"SendbirdMigration | creating conversation for sendbird_message_id: {sendbird_message_id}"
                    f" with user_id: {user_id} & request_body: {req_body}"
                )
            )

            # self._join_secret_chatroom_before_create_conversation(user_id, chatroom_id, sendbird_message_id)

            conversation_response = self._create_conversation(
                user_id=user_id,
                platform_code=self.platform_code,
                version_code=self.version_code,
                req_body=req_body,
                created_at=created_at,
                is_deleted=is_deleted
            )

            conversation_id = conversation_response.get("id")

            # Set cache for conversation_id
            CacheImpl.set_cache(SENDBIRD_MESSAGE_MAP_KEY.format(community_id, sendbird_message_id), conversation_id,
                                timeout=TTL_FOR_CACHE)

            info_logger.info(
                (
                    f"SendbirdMigration | Conversation created for sendbird_message_id: {sendbird_message_id} "
                    f" with conversation_id: {conversation_id} & chatroom_id: {chatroom_id}"
                )
            )

        if reactions:

            info_logger.info(
                (
                    f"SendbirdMigration | Creating reactions for conversation_id: {conversation_id}" 
                    f" with reactions: {reactions}"
                )
            )

            self._create_reactions_for_message(reactions, conversation_id, chatroom_id)

            info_logger.info(
                (
                    f"SendbirdMigration | Reactions created for conversation_id: {conversation_id} "
                    f"with reactions: {reactions}"
                )
             )

        polls = conversation_response.get("conversation", {}).get("polls")
        if polls and poll_options:

            info_logger.info(
                (
                    f"SendbirdMigration | Creating poll votes for conversation_id: {conversation_id}"
                    f"with polls: {polls} & poll_options: {poll_options}"
                )
            )

            self._create_poll_votes(conversation_id, polls, poll_options)

            info_logger.info(
                (
                    f"SendbirdMigration | Poll votes created for conversation_id: {conversation_id} " 
                    f"with polls: {polls} & poll_options: {poll_options}"
                )
            )

        return conversation_response

    @staticmethod
    def _join_secret_chatroom_before_create_conversation(user_id: int, chatroom_id: int, sendbird_message_id: str):
        # Join chatroom if chatroom is secret
        from collabmates_api.chatroom.chatroom_impl import ChatroomImpl

        chatroom_manager = ChatroomImpl(user_id, chatroom_id=chatroom_id)

        req_body = {
            "chatroom_id": chatroom_id,
            "secret_chatroom_participants": [user_id],
            "is_channel_invite": False,
        }

        response = chatroom_manager.add_secret_chatroom_participant(req_body)
        info_logger.info(
            (
                f"SendbirdMigration | User joined chatroom for sendbird_message_id: {sendbird_message_id} "
                f"with user_id: {user_id} & chatroom_id: {chatroom_id} | response: {response}"
            )
        )

    def create_all_messages(self):
        info_logger.info(
            (
                f"SendbirdMigration | Total messages to be added: {len(self.messages_data)}"
            )
        )

        for message_data in self.messages_data:
            sendbird_message_id = message_data.sendbird_message_id

            if message_data.sendbird_parent_msg_id:
                lm_parent_conversation_id = MigrationUtils.get_lm_id_from_sendbird_message_id(
                    message_data.sendbird_parent_msg_id, self.community_id
                )
                if lm_parent_conversation_id:
                    message_data.replied_conversation_id = lm_parent_conversation_id
                else:
                    info_logger.error(
                        (
                            f"SendbirdMigration | No conversation id found in the cache for sendbird_parent_msg_id: "
                            f"{sendbird_message_id}"
                        )
                    )
                    continue
            try:
                request_body = message_data.model_dump(
                    include=[
                        "text",
                        "state",
                        "chatroom_id",
                        "attachments",
                        "replied_conversation_id",
                        "metadata",
                        "og_tags",
                        "polls",
                        "poll_type",
                        "expiry_time",
                        "no_poll_expiry",
                        "allow_add_option",
                        "multiple_select_state",
                        "multiple_select_no"
                    ]
                )

                is_deleted = message_data.is_deleted
                created_at = message_data.created_at
                chatroom_id = message_data.chatroom_id
                user_id = message_data.user_id

                reactions = message_data.reactions
                poll_options = message_data.polls

                # Create Conversation and its related data
                self._create_conversation_and_its_related_data(
                    sendbird_message_id=sendbird_message_id,
                    user_id=user_id,
                    community_id=self.community_id,
                    req_body=request_body,
                    chatroom_id=chatroom_id,
                    created_at=created_at,
                    is_deleted=is_deleted,
                    reactions=reactions,
                    poll_options=poll_options,
                )

            except Exception as e:
                info_logger.error(
                    (
                        f"SendbirdMigration | Error in creating conversation for sendbird_message_id: "
                        f" {sendbird_message_id}: | Error: {e} | Traceback: {traceback.format_exc()}"
                    )
                )

                continue
