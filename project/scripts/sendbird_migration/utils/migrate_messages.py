from typing import List

from ..models.message import MessageModel, ReactionModel, MessageUtilites
from ..constants import PLATFORM_CODE, VERSION_CODE, LIKEMINDS_API_KEY
from ..models.message import CONVERSATION_LM_KEY #TODO: Move to constants

from collabmates_api.conversation.conversation_impl import ConversationImpl
from utility.version_utilities import VersionUtilities
from external_services.caching.cache_impl import CacheImpl

TTL_FOR_CACHE = 60 * 60 * 60 #TODO: Move to constants

class MigrateMessages:
    
    api_key: str = ""
    platform_code: str = ""
    version_code: str = ""

    messages_data = []
    
    def __init__(self, api_key: str, platform_code: str, version_code: str, messages_data: List[MessageModel]):
        
        self.api_key = api_key
        self.platform_code = platform_code
        self.version_code = version_code
        self.messages_data = messages_data
        
    def _create_convesation_and_its_related_data(self, sendbird_message_id: str,  user_id: int, req_body: dict, 
                                                 chatroom_id: int, created_at: int, is_deleted: bool, 
                                                 reactions: List[ReactionModel] = None, poll_votes=None):

        conversation_id = CacheImpl.get_cache(CONVERSATION_LM_KEY.format(sendbird_message_id))
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
            if not conversation_id :
                raise ValueError(f"Cannot find conversation_id in response for message_id: {sendbird_message_id} | conversation_response: {conversation_response}")
            
            # Set cache for conversation_id
            CacheImpl.set_cache(CONVERSATION_LM_KEY.format(sendbird_message_id), conversation_id, timeout=TTL_FOR_CACHE)

            print(f"Conversation created for sendbird_message_id: {sendbird_message_id} with conversation_id: {conversation_id} & chatroom_id: {chatroom_id}")
    
        if reactions:

            print(f"Creating reactions for conversation_id: {conversation_id} with reactions: {reactions}")

            self._create_reactions_for_message(reactions, conversation_id, chatroom_id)

            print(f"Reactions created for conversation_id: {conversation_id} with reactions: {reactions}")

        if poll_votes:
            #TODO: Add poll votes
            pass

        return conversation_response

    def _create_conversation(self, user_id: int, api_key: str, platform_code: str, version_code: str, req_body: dict, 
                             created_at: int, is_deleted: bool):
        
        conversaton_manager = ConversationImpl(
            member_id=user_id,
            request_platform=platform_code,
            version_code=version_code,
            api_key=api_key,
            api_version_code=VersionUtilities.APIVersionCodes.V1.value
        )

        # Create Message
        conversation_response = conversaton_manager.create_conversation_v1(req_body)
        if conversation_response.get("error_message"):
            raise ValueError(f"Error in create_conversation_v1: {conversation_response.get('error_message')} | req_body: {req_body} | user_id: {user_id}")
        

        #TODO: Update created_at and is_deleted for message and its attachments if any

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
                    raise ValueError(f"Error in add_reaction: {reaction_response.get('error_message')} | user_id: {reaction_user_id} | reaction: {reaction} | conversation_id: {conversation_id} | chatroom_id: {chatroom_id}")
                
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
                poll_votes = message_data.poll_votes

                # Create Conversation and its related data
                self._create_convesation_and_its_related_data(
                    sendbird_message_id=sendbird_message_id,
                    user_id=user_id,
                    req_body=request_body,
                    chatroom_id=chatroom_id,
                    created_at=created_at,
                    is_deleted=is_deleted,
                    reactions=reactions,
                    poll_votes=poll_votes
                )

            except Exception as e:
                print(f"Error in creating conversation for sendbird_message_id: {sendbird_message_id}: {e}")
                continue
