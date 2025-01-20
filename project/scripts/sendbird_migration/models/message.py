import json, mimetypes, traceback

from typing import List, Optional
from pydantic import BaseModel, Field, model_validator, ValidationError

from pydantic_core import PydanticCustomError

from ..models.user import UserModel
from ..models.channel import ChannelModel
from ..utils.lambda_utilities import LambdaUtilities
from ..constants import (SENDBIRD_USER_MAP_KEY, SENDBIRD_CHANNEL_MAP_KEY, SENDBIRD_MESSAGE_MAP_KEY, 
                         USER_PROFILE_ROUTE, MENTIONED_USERS_SYMBOL, CONVERATION_FILE_S3_PATH, DEFAULT_FILE_S3_PATH)

from utility.time_utilities import TimeUtilities
from utility.states import conversation_states, card_types, multi_select_poll_states, attachment_types
from external_services.caching.cache_impl import CacheImpl


class MessageUtilites:

    @staticmethod
    def get_lm_id_from_sendbird_message_id(sendbird_message_id: int, community_id: int) -> int:

        lm_id = CacheImpl.get_cache(SENDBIRD_MESSAGE_MAP_KEY.format(community_id, sendbird_message_id))
        if not lm_id:
            print(f"No conversation id found in the cache for sendbird message id: {sendbird_message_id}")
            return None
        
        return lm_id
    
    @staticmethod
    def get_lm_user_id_from_sendbird_user_id(sendbird_user_id: str, community_id: int) -> int:
        lm_user_id = CacheImpl.get_cache(SENDBIRD_USER_MAP_KEY.format(community_id, sendbird_user_id))
        if not lm_user_id:
            print( f"No user id found in the cache for sendbird user id: {sendbird_user_id}")
            return None
        
        return lm_user_id
    
    @staticmethod
    def get_file_path_for_conversation_files(chatroom_id: int, user_id: int) -> str:
        
        if not (chatroom_id and user_id):
            print(f"No chatroom id or user_id found for conversation files.")
            return DEFAULT_FILE_S3_PATH
        
        return CONVERATION_FILE_S3_PATH.format(chatroom_id, user_id)

    # function to replace mentions
    def replace_mentions(text, users):
        while users:
            text = text.replace(MENTIONED_USERS_SYMBOL, users.pop(0), 1)
        return text
    
    def ensure_epoch_in_ms(epoch_time):
        # Check if the epoch time is in seconds (10 digits) or milliseconds (13 digits)
        if len(str(epoch_time)) == 10:
            # Convert seconds to milliseconds
            return epoch_time * 1000
        return epoch_time


class AttachmentModel(BaseModel):
    url: str = ""
    type: str = ""
    name: str = ""
    index: int = 0
    thumbnail_url: str = ""
    height: int =  None
    width: int = None

    user_id: int = 0
    chatroom_id: int = 0
    community_id: int = 0

    attachment_message: str = ""
    replied_conversation_id: int = 0

    def _validate_file_name(data):

        if data.get('file_name'):
            data["name"] = data.get('file_name')

        return data

    def _validate_url(data):

        url = data.get('url')
        if url:
            file_path = MessageUtilites.get_file_path_for_conversation_files(data.get('chatroom_id'), data.get('user_id'))
            attachment_url = LambdaUtilities.migrate_to_s3(url, file_path)
            if attachment_url:
                data["url"] = attachment_url

        return data

    def _validate_type(data):

        sendbird_type = data.get("file_type") or data.get("type")
        if not sendbird_type:
            raise PydanticCustomError("invalid_attachment_type", "No attachment type found in the attachment.")

        # Extract the first word after the "/" in the MIME type string
        parts = sendbird_type.split('/')
        if len(parts) > 1:
            main_type = parts[0]

            # Determine the type based on the main type
            if main_type == 'image':
                if sendbird_type == 'image/gif':
                    data["type"] = 'gif'
                else:
                    data["type"] = 'image'
            elif main_type == 'audio':
                data["type"] = 'audio'
            elif main_type == 'video':
                data["type"] = 'video'
            else:
                raise PydanticCustomError("invalid_attachment_type", "Unsupported attachment type found in the attachment.")

        return data

    @staticmethod
    def _validate_thumbnail_urls(data):

        if data.get('thumbnails'):
            file_path = MessageUtilites.get_file_path_for_conversation_files(data.get('chatroom_id'), data.get('user_id'))
            url = data.get('thumbnails')[0].get('url')
            if url:
                thumbnail_url = LambdaUtilities.migrate_to_s3(url, file_path)
                if thumbnail_url:
                    data["thumbnail_url"] = thumbnail_url

        return data

    @staticmethod
    def _validate_misfits_keys(data, metadata):

        message = metadata.get('msg')
        if message:
            data["attachment_message"] = message

        name = metadata.get('name')
        if name:
            data["name"] = name

        file_width = metadata.get('fileWidth')
        if file_width:
            data["width"] = file_width


        file_height = metadata.get('fileHeight')
        if file_height:
            data["height"] = file_height

        type = metadata.get('type')
        if type:
            if attachment_types.is_valid_attachment_type(type):
                data["type"] = type
            else:
                print(f"Invalid attachment type found in the misfits Type: {type}")
            
        url = metadata.get('fileUrl')
        if url:
            file_path = MessageUtilites.get_file_path_for_conversation_files(metadata.get('chatroom_id'), metadata.get('user_id'))
            attachment_url = LambdaUtilities.migrate_to_s3(url, file_path)
            if attachment_url:
                data["url"] = attachment_url

        thumbnail_url = metadata.get('videoThumbnailUrl')
        if thumbnail_url:
            file_path = MessageUtilites.get_file_path_for_conversation_files(metadata.get('chatroom_id'), metadata.get('user_id'))
            url = LambdaUtilities.migrate_to_s3(thumbnail_url, file_path)
            if url:
                data["thumbnail_url"] = thumbnail_url

        parent_message = metadata.get('parentMessage')
        if parent_message:

            parent_message_id = parent_message.get("message_id")
            if parent_message_id:

                community_id = metadata.get("community_id")
                if not community_id:
                    raise PydanticCustomError("invalid_community_id", "No community id found in the attachment.")
                
                lm_id = MessageUtilites.get_lm_id_from_sendbird_message_id(parent_message_id, community_id)
                if not lm_id:
                    print(f"No conversation id found in the cache for sendbird message id: {parent_message_id}")
                else:
                    data["replied_conversation_id"] = lm_id
            
        return data
    
    def _populate_misfits_metadata(data):

        metadata = data.get('data')
        if metadata:
            try:
                metadata = json.loads(metadata)
                if metadata:
                    data = AttachmentModel._validate_misfits_keys(data, metadata)
                    
            except json.JSONDecodeError:
                raise PydanticCustomError("invalid_metadata", "Invalid metadata found in the attachment.")
        
        return data

    @model_validator(mode="before")
    def _validate_before(cls, data):
        data = cls._validate_file_name(data)
        data = cls._validate_url(data)
        data = cls._validate_type(data)
        data = cls._validate_thumbnail_urls(data)
        data = cls._validate_misfits_keys(data, data)

        data = cls._populate_misfits_metadata(data)

        return data


class PollOptionsModel(BaseModel):
    text: str


class ReactionModel(BaseModel):
    reaction_key: str = Field(alias="key")
    user_ids: List[int] = []
    community_id: int = 0

    @model_validator(mode="before")
    def _validate_user_ids(cls, data):

        users_list = data.get("user_ids")
        if not users_list:
            print(f"No user ids found in the reaction for key: {data.get('reaction_key')}")
            return data
        
        lm_user_ids = []
        
        for user_id in users_list:

            community_id = data.get("community_id")
            if not community_id:
                raise PydanticCustomError("invalid_community_id", "No community id found in the reaction.")

            lm_user_id = MessageUtilites.get_lm_user_id_from_sendbird_user_id(user_id, community_id)
            if not lm_user_id:
                print(f"No user id found in the cache for sendbird user id: {user_id} for reaction key: {data.get('reaction_key')}")
                continue
            
            lm_user_ids.append(lm_user_id)

        data["user_ids"] = lm_user_ids

        return data

class OgTagsModel(BaseModel):
    title: str
    description: str
    image: str
    url: str


class MessageModel(BaseModel):
    sendbird_message_id: int = Field(alias="message_id")
    is_deleted: bool = Field(alias="is_removed", default=False)
    created_at: int = 0
    user_id: int = 0
    community_id: int = 0

    state: int = 0
    text: str = ""
    chatroom_id: int = 0

    attachments: Optional[List[AttachmentModel]] = []
    replied_conversation_id: int = 0
    metadata: dict = {}
    og_tags: Optional[OgTagsModel] = None

    polls: List[PollOptionsModel] = []
    poll_type: int = 2 # Default poll type is 2 (Open Poll)
    expiry_time: int = 0
    no_poll_expiry: bool = False
    allow_add_option: bool = False
    multiple_select_state: Optional[str] = Field(default=None)
    multiple_select_no: Optional[int] = Field(default=0)

    reactions: List[ReactionModel] = []

    def _validate_state(data):
        # Validate the state
        conversation_states_dict = {
            "MESG": conversation_states.ANSWER, 
            "FILE": conversation_states.ANSWER
        }

        if not (data.get("type") and data.get("type") in conversation_states_dict):
            raise PydanticCustomError("invalid_message_type", "Invalid message type.")

        data["state"] = conversation_states_dict[data.get("type")]
        return data

    def _validate_user(data):

        # Fetch user_id
        user_id = data.get("user", {}).get("user_id")
        if not user_id:
            raise PydanticCustomError("invalid_user_id", "No user id found in the message.")
        
        community_id = data.get("community_id")
        if not community_id:
            raise PydanticCustomError("invalid_community_id", "No community id found in the message.")

        # Fetch likeminds user_id from cache
        lm_user_id =  MessageUtilites.get_lm_user_id_from_sendbird_user_id(user_id, community_id)
        if not lm_user_id:
            raise PydanticCustomError("invalid_user_id", "No user id found in the cache.")

        data["user_id"] = lm_user_id

        return data

    def _validate_message(data):

        if data.get("message"):
            data["text"] = data.get("message")

        return data

    def _validate_chatroom_id(data):

        # Fetch chatroom_id
        channel_url = data.get("channel_url")
        if not channel_url:
            raise PydanticCustomError("invalid_chatroom_id", "No chatroom id found in the message.")
        
        community_id = data.get("community_id")
        if not community_id:
            raise PydanticCustomError("invalid_community_id", "No community id found in the message.")

        # Fetch likeminds chatroom_id from cache
        lm_chatroom_id =  CacheImpl.get_cache(SENDBIRD_CHANNEL_MAP_KEY.format(community_id, channel_url))
        if not lm_chatroom_id:
            raise PydanticCustomError("invalid_chatroom_id", "No chatroom id found in the cache.")

        data["chatroom_id"] = lm_chatroom_id

        return data

    def _validate_attachments(data):

        if data.get('type') == 'FILE':

            file_data = data.get("file")
            files_data = data.get("files")
            if not (file_data or files_data):
                raise PydanticCustomError("invalid_attachment", "No file/s found in the message.")

            data["attachments"] = []

            user_id = data.get("user_id")
            chatroom_id = data.get("chatroom_id")

            if not user_id or not chatroom_id:
                print(f"No user user_id or chatroom id found in the message data: {data}")
                return data
            
            if file_data:
                file_data["index"] = len(data["attachments"]) + 1
                attachment = AttachmentModel(**file_data, user_id=user_id, chatroom_id=chatroom_id)
                data["attachments"].append(attachment)

                return data

            if files_data:
                for index, file_data in enumerate(files_data):
                    attachment = AttachmentModel(**file_data, index=index, user_id=user_id, chatroom_id=chatroom_id)
                    data["attachments"].append(attachment)
                    

        return data

    def _validate_replied_conversation_id(data):

        if data.get('replied_conversation_id'):

            community_id = data.get("community_id")
            if not community_id:
                raise PydanticCustomError("invalid_community_id", "No community id found in the message.")

            # Fetch LM conversation_id from cache
            conversation_id = MessageUtilites.get_lm_id_from_sendbird_message_id(data.get('replied_conversation_id'), community_id)
            if not conversation_id:
                print(f"No conversation id found in the cache for sendbird message id: {data.get('replied_conversation_id')}")
            else:
                data["replied_conversation_id"] = conversation_id

        return data

    def _validate_created_at(data):

        created_at = data.get("created_at")
        if not created_at:
            raise PydanticCustomError("invalid_created_at", "No created_at found in the message.")

        data["created_at"] = MessageUtilites.ensure_epoch_in_ms(created_at)

        return data
    
    def _validate_reactions(data):

        reactions_data = data.get("reactions")
        if reactions_data:
            reactions_list = []
            for reaction in reactions_data:
                reactions = ReactionModel(**reaction, community_id=data.get("community_id"))
                reactions_list.append(reactions)

            data["reactions"] = reactions_list

        return data

    def _populate_polls(data):

        poll_data = data.get("poll")

        if poll_data:
            data["state"] = conversation_states.CONVERSATION_POLL

            if poll_data.get("title"):
                data["text"] = poll_data.get("title")

            if poll_data.get("close_at"):
                if poll_data.get("close_at", 0) <= 0:
                    data["no_poll_expiry"] = True
                else:
                    data["expiry_time"] = MessageUtilites.ensure_epoch_in_ms(poll_data.get("close_at"))

            if poll_data.get("options"):
                data["polls"] = [
                    PollOptionsModel(text=poll_option.get("text"))
                    for poll_option in poll_data.get("options")
                ]

            if poll_data.get("allow_multiple_votes"):
                data["multiple_select_state"] = multi_select_poll_states.AT_MAX
                data["multiple_select_no"] = len(poll_data.get("options"))

            if poll_data.get("allow_user_suggestion"):
                data["allow_add_option"] = True

        return data

    def _populate_mentions(data):

        if data.get("mentioned_users"):

            mentioned_user_lm_routes = []
            for user in data.get("mentioned_users"):
                user_id = user.get("user_id")
                if not user_id:
                    raise PydanticCustomError(
                        "invalid_user_id", "No user id found in the mentioned users."
                    )
                
                lm_user_id = MessageUtilites.get_lm_user_id_from_sendbird_user_id(user_id, data.get("community_id"))

                user_name = user.get("nickname")
                if not user_name:
                    raise PydanticCustomError(
                        "invalid_user_name",
                        "No user name found in the mentioned users.",
                    )

                # Using user_id as uuid to create user mention route
                user_mention_route = USER_PROFILE_ROUTE.format(user_name, lm_user_id)
                mentioned_user_lm_routes.append(user_mention_route)

            # Replace all 'SYMBOL' in the message with the mentioned users
            message = MessageUtilites.replace_mentions(data.get("text"), mentioned_user_lm_routes)
            data["text"] = message

        return data

    def _populate_misfits_metadata(data):

        if data.get('data'):
            # Parse JSON data from the message
            try:
                metadata = json.loads(data.get('data'))

                parent_message = metadata.get("parentMessage")
                if parent_message:

                    parent_message_id = parent_message.get("message_id")
                    if parent_message_id:

                        community_id = data.get("community_id")
                        if not community_id:
                            raise PydanticCustomError("invalid_community_id", "No community id found in the message.")
                        
                        lm_id = MessageUtilites.get_lm_id_from_sendbird_message_id(parent_message_id, community_id)
                        if not lm_id:
                            print(f"No conversation id found in the cache for sendbird message id: {parent_message_id}")
                        else:
                            data["replied_conversation_id"] = lm_id

                type = metadata.get("type")
                if type == "multi-media":
                    
                    attachments = metadata.get("metaData")
                    if attachments:

                        lm_attachments = []
                        index = len(data.get("attachments", [])) if data.get("attachments") else 0

                        user_id = data.get("user_id")
                        chatroom_id = data.get("chatroom_id")

                        if not user_id or not chatroom_id:
                            print(f"No user user_id or chatroom id found in the message data: {data}")
                            return data

                        for _, attachment in enumerate(attachments):
                            lm_attachments.append(AttachmentModel(**attachment, index=index, user_id=user_id, chatroom_id=chatroom_id))
                            index += 1

                        data["attachments"] = (lm_attachments)

            except json.JSONDecodeError:
                raise PydanticCustomError("invalid_metadata", "Invalid metadata found in the message.")

        return data

    def _populate_misfits_attachment_meta(data):

        attachments = data.get('attachments', [])
        for attachment in attachments:
            if attachment.attachment_message:
                data["text"] = attachment.attachment_message if not attachment.attachment_message == "file" else data.get("text")
            
            if attachment.replied_conversation_id:
                data["replied_conversation_id"] = attachment.replied_conversation_id

        return data
    
    @model_validator(mode="before")
    def _validate_before(cls, data):

        data = cls._validate_state(data)
        data = cls._validate_user(data)
        data = cls._validate_message(data)
        data = cls._validate_chatroom_id(data)
        data = cls._validate_attachments(data)
        data = cls._validate_replied_conversation_id(data)
        data = cls._validate_created_at(data)
        data = cls._validate_reactions(data)
        data = AttachmentModel._validate_thumbnail_urls(data)

        data = cls._populate_polls(data)
        data = cls._populate_mentions(data)
        data = cls._populate_misfits_metadata(data)
        data = cls._populate_misfits_attachment_meta(data)

        return data


class Messages(BaseModel):
    messages: List[MessageModel]

    @model_validator(mode="before")
    def validate_messages(cls, values):

        validated_messages = []

        for message in values.get('messages', []):
            try:

                if message.get('type') == 'ADMM':
                    # Skip admin messages
                    print(f"Skipping ADMM (Admin) message {message.get('message_id')}")
                    continue

                validated_message = MessageModel(**message)
                validated_messages.append(validated_message)

            except ValidationError as e:
                traceback.print_exc()
                print(f"Validation error for message_id: {message.get('message_id')} | Exception: {e}")
                # Handle validation errors as needed
                continue
               
            except Exception as e:
                print(f"Unexpected error for message {message.get('message_id')}: {e}")
                # Print stack trace
                traceback.print_exc()
                # Handle other exceptions as needed
                raise e

        values['messages'] = validated_messages
        return values