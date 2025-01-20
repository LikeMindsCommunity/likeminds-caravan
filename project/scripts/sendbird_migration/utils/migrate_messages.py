import traceback
from typing import List

from ..models.message import MessageModel, ReactionModel, MessageUtilites
from ..constants import SENDBIRD_MESSAGE_MAP_KEY
from ..constants import TTL_FOR_CACHE

from togther.models import ModelUtilities, card_answers, conversationPolls, answerAttachment
from collabmates_api.conversation.conversation_impl import ConversationImpl
from utility.version_utilities import VersionUtilities
from external_services.caching.cache_impl import CacheImpl

class MigrateMessages:
    
    api_key: str = ""
    platform_code: str = ""
    version_code: str = ""
    community_id: int = None

    messages_data = []
    
    def __init__(self, api_key: str, community_id: int, platform_code: str, version_code: str, 
                 messages_data: List[MessageModel]):
        
        self.api_key = api_key
        self.community_id = community_id
        self.platform_code = platform_code
        self.version_code = version_code
        self.messages_data = messages_data
        
    def _create_convesation_and_its_related_data(self, sendbird_message_id: str,  user_id: int, community_id: int, 
                                                 req_body: dict, chatroom_id: int, created_at: int, is_deleted: bool, 
                                                 reactions: List[ReactionModel] = None):

        conversation_id = CacheImpl.get_cache(SENDBIRD_MESSAGE_MAP_KEY.format(community_id,sendbird_message_id))
        if conversation_id:
            print(f"Conversation already created for sendbird_message_id: {sendbird_message_id}")
            return
        else:

            print(f"Create conversation for sendbird_message_id: {sendbird_message_id} with user_id: {user_id} & request_body: {req_body}")

            conversation_response = self._create_conversation(
                user_id=user_id,
                api_key=self.api_key,
                platform_code=self.platform_code,
                version_code=self.version_code,
                req_body=req_body,
                created_at=created_at,
                is_deleted=is_deleted
            )
        
            conversation_id = conversation_response.get("id")
            
            # Set cache for conversation_id
            CacheImpl.set_cache(SENDBIRD_MESSAGE_MAP_KEY.format(community_id,sendbird_message_id), conversation_id, timeout=TTL_FOR_CACHE)

            print(f"Conversation created for sendbird_message_id: {sendbird_message_id} with conversation_id: {conversation_id} & chatroom_id: {chatroom_id}")
    
        if reactions:

            print(f"Creating reactions for conversation_id: {conversation_id} with reactions: {reactions}")

            self._create_reactions_for_message(reactions, conversation_id, chatroom_id)

            print(f"Reactions created for conversation_id: {conversation_id} with reactions: {reactions}")

        polls = conversation_response.get("conversation", {}).get("polls")
        if polls:
            #TODO: For each poll options, fetch poll votes from API and create poll votes
            pass

        return conversation_response

    def _create_conversation(self, user_id: int, api_key: str, platform_code: str, version_code: str, req_body: dict, 
                             created_at: int, is_deleted: bool):
        
        conversaton_manager = ConversationImpl(
            member_id=user_id,
            platform_code=platform_code,
            version_code=version_code,
            api_version_code=VersionUtilities.APIVersionCodes.V1.value
        )

        # Create Message
        conversation_response = conversaton_manager.create_conversation_v1(req_body)
        if conversation_response.get("error_message"):
            raise ValueError(f"Error in create_conversation_v1: {conversation_response.get('error_message')} | req_body: {req_body} | user_id: {user_id}")
        
        conversation_id = conversation_response.get("id")
        if not conversation_id:
            raise ValueError(f"Cannot find conversation_id in response for user_id: {user_id} | conversation_response: {conversation_response}")

        # Update convesation created_at and is_deleted
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
                
    def _create_reactions_for_message(self, reactions: List[ReactionModel], conversation_id: int, chatroom_id: int):
        
        for reaction in reactions:
            for reaction_user_id in reaction.user_ids:
                conversation_manager = ConversationImpl(
                    member_id=reaction_user_id,
                    chatroom_id=chatroom_id,
                    conversation_id=conversation_id,
                )

                reaction_response = conversation_manager.add_reaction(reaction.reaction_key)
                if reaction_response.get("error_message"):
                    print(f"Error in add_reaction: {reaction_response.get('error_message')} | user_id: {reaction_user_id} | reaction: {reaction} | conversation_id: {conversation_id} | chatroom_id: {chatroom_id}")
                    raise ValueError(reaction_response.get("error_message"))
                
        return 
    
    def create_all_messages(self):
        
        print("*" * 50)
        print(f"Total messages to be added: {len(self.messages_data)}")
        
        for message_data in self.messages_data:

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
                        "expiry_time",
                        "no_poll_expiry",
                        "allow_add_option",
                        "multiple_select_state",
                        "multiple_select_no"
                    ]
                )

                sendbird_message_id = message_data.sendbird_message_id
                is_deleted = message_data.is_deleted
                created_at = message_data.created_at
                chatroom_id = message_data.chatroom_id
                user_id = message_data.user_id

                reactions = message_data.reactions

                # Create Conversation and its related data
                self._create_convesation_and_its_related_data(
                    sendbird_message_id=sendbird_message_id,
                    user_id=user_id,
                    community_id=self.community_id,
                    req_body=request_body,
                    chatroom_id=chatroom_id,
                    created_at=created_at,
                    is_deleted=is_deleted,
                    reactions=reactions,
                )

            except Exception as e:
                print(f"Error in creating conversation for sendbird_message_id: {sendbird_message_id}: {e}")
                traceback.print_exc()
                continue
