import json, mimetypes

from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
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
            print("No conversation id found in the cache for sendbird message id: %d" % sendbird_message_id)
            return None
        
        return lm_id
    
    @staticmethod
    def get_lm_user_id_from_sendbird_user_id(sendbird_user_id: str, community_id: int) -> int:
        lm_user_id = CacheImpl.get_cache(SENDBIRD_USER_MAP_KEY.format(community_id, sendbird_user_id))
        if not lm_user_id:
            print("No user id found in the cache for sendbird user id: %d" % sendbird_user_id)
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
    url: str
    type: str
    name: str = Field(alias="file_name")
    index: int
    thumbnail_url: str
    height: int =  None
    width: int = None

    user_id: int = 0
    chatroom_id: int = 0
    community_id: int = 0

    attachment_message: str 
    replied_conversation_id: int = 0

    @staticmethod
    def _validate_url(data):

        url = data.get('url')
        if url:
            file_path = MessageUtilites.get_file_path_for_conversation_files(data.get('chatroom_id'), data.get('user_id'))
            attachment_url = LambdaUtilities.migrate_to_s3(url, file_path)
            if attachment_url:
                data["url"] = attachment_url

        return data

    @staticmethod
    def _validate_type(data):

        type = ''

        sendbird_type = data.get("file_type")
        if not sendbird_type:
            raise PydanticCustomError("invalid_attachment_type", "No attachment type found in the attachment.")

        # Validate the attachment type
        mime_type, _ = mimetypes.guess_type(sendbird_type)
        if not mime_type:
            raise PydanticCustomError("invalid_attachment_type", "Invalid attachment type found in the attachment.")

        if mime_type.startswith('image/'):
            if mime_type == 'image/gif':
                type = 'gif'
            else:
                type = 'image'
        elif mime_type.startswith('audio/'):
            type = 'audio'
        elif mime_type.startswith('video/'):
            type = 'video'

        data["type"] = type

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

    @classmethod
    @model_validator(mode="before")
    def _validate_before(cls, data):
        data = cls._validate_url(data)
        data = cls._validate_type(data)
        data = cls._validate_thumbnail_urls(data)

        return data
    
    @staticmethod
    def _validate_misfits_keys(data):

        message = data.get('msg')
        if message:
            data["attachment_message"] = message

        name = data.get('name')
        if name:
            data["name"] = name

        file_width = data.get('fileWidth')
        if file_width:
            data["width"] = file_width


        file_height = data.get('fileHeight')
        if file_height:
            data["height"] = file_height

        type = data.get('type')
        if type:
            if attachment_types.is_valid_attachment_type(type):
                data["type"] = type
            else:
                raise PydanticCustomError("invalid_attachment_type", f"Invalid attachment type found in the misfits Type: {type}")
            
        url = data.get('fileUrl')
        if url:
            file_path = MessageUtilites.get_file_path_for_conversation_files(data.get('chatroom_id'), data.get('user_id'))
            attachment_url = LambdaUtilities.migrate_to_s3(url, file_path)
            if attachment_url:
                data["url"] = attachment_url

        thumbnail_url = data.get('videoThumbnailUrl')
        if thumbnail_url:
            file_path = MessageUtilites.get_file_path_for_conversation_files(data.get('chatroom_id'), data.get('user_id'))
            url = LambdaUtilities.migrate_to_s3(thumbnail_url, file_path)
            if url:
                data["thumbnail_url"] = thumbnail_url

        parent_message = data.get('parentMessage')
        if parent_message:

            parent_message_id = parent_message.get("message_id")
            if parent_message_id:

                community_id = data.get("community_id")
                if not community_id:
                    raise PydanticCustomError("invalid_community_id", "No community id found in the attachment.")
                
                lm_id = MessageUtilites.get_lm_id_from_sendbird_message_id(parent_message_id, community_id)
                if not lm_id:
                    raise PydanticCustomError("invalid_replied_conversation_id", "No replied conversation id found in the cache.")
                
                data["replied_conversation_id"] = lm_id
            
        return data
    
    @staticmethod
    def _populate_misfits_metadata(data):

        metadata = data.get('data')
        if metadata:
            try:
                metadata = json.loads(metadata)
                if metadata:
                    data = AttachmentModel._validate_misfits_keys(metadata)
                    
            except json.JSONDecodeError:
                raise PydanticCustomError("invalid_metadata", "Invalid metadata found in the attachment.")
        
        return data

    @classmethod
    @model_validator(mode="after")
    def _validate_after(cls, data):
        data = cls._validate_misfits_keys(data)
        data = cls._populate_misfits_metadata(data)

        return data


class PollOptionsModel(BaseModel):
    text: str


class ReactionModel(BaseModel):
    reaction_key: str = Field(alias="key")
    user_ids: List[int] = []
    community_id: int = 0

    @classmethod
    @model_validator(mode="before")
    def _validate_user_ids(cls, data):

        users_list = data.get("user_ids")
        if not users_list:
            print(f"No user ids found in the reaction for key: {data.get('reaction_key')}")
            return data
        
        for user_id in users_list:

            community_id = data.get("community_id")
            if not community_id:
                raise PydanticCustomError("invalid_community_id", "No community id found in the reaction.")

            lm_user_id = MessageUtilites.get_lm_user_id_from_sendbird_user_id(user_id, community_id)
            if not lm_user_id:
                print(f"No user id found in the cache for sendbird user id: {user_id} for reaction key: {data.get('reaction_key')}")
                continue
            
            data["user_ids"].append(lm_user_id)

        return data


class OgTagsModel(BaseModel):
    title: str
    description: str
    image: str
    url: str


class MessageModel(BaseModel):
    sendbird_message_id: int = Field(alias="message_id")
    is_deleted: bool = Field(alias="is_removed")
    created_at: int
    user_id: int
    community_id: int

    state: int = 0
    text: str = Field(alias="message")
    chatroom_id: int = Field(alias="channel_id")

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

    # @root_validator(pre=True)
    # def pass_user_id_and_chatroom_id

    @staticmethod
    def _validate_state(data):
        # Validate the state
        conversation_states_dict = {"MESG": conversation_states.ANSWER, "FILE": conversation_states.ANSWER }

        if not (data.get("type") and data.get("type") in conversation_states_dict):
            raise PydanticCustomError("invalid_message_type", "Invalid message type.")

        data["state"] = conversation_states_dict[data.get("type")]
        return data

    @staticmethod
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

    @staticmethod
    def _validate_chatroom_id(data):

        # Fetch chatroom_id
        chatroom_id = data.get("channel_id")
        if not chatroom_id:
            raise PydanticCustomError("invalid_chatroom_id", "No chatroom id found in the message.")
        
        community_id = data.get("community_id")
        if not community_id:
            raise PydanticCustomError("invalid_community_id", "No community id found in the message.")

        # Fetch likeminds chatroom_id from cache
        lm_chatroom_id =  CacheImpl.get_cache(SENDBIRD_CHANNEL_MAP_KEY.format(community_id, chatroom_id))
        if not lm_chatroom_id:
            raise PydanticCustomError("invalid_chatroom_id", "No chatroom id found in the cache.")

        data["chatroom_id"] = lm_chatroom_id

        return data

    @staticmethod
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

            if files_data:
                for index, file_data in enumerate(files_data):
                    attachment = AttachmentModel(**file_data, index=index, user_id=user_id, chatroom_id=chatroom_id)
                    data["attachments"].append(attachment)

            if file_data:
                file_data["index"] = len(data["attachments"]) + 1
                attachment = AttachmentModel(**file_data, user_id=user_id, chatroom_id=chatroom_id)
                data["attachments"].append(attachment)

        return data

    @staticmethod
    def _validate_replied_conversation_id(data):

        if data.get('replied_conversation_id'):

            community_id = data.get("community_id")
            if not community_id:
                raise PydanticCustomError("invalid_community_id", "No community id found in the message.")

            # Fetch LM conversation_id from cache
            conversation_id = MessageUtilites.get_lm_id_from_sendbird_message_id(data.get('replied_conversation_id'), community_id)
            if not conversation_id:
                raise PydanticCustomError("invalid_replied_conversation_id", "No replied conversation id found in the cache.")

            data["replied_conversation_id"] = conversation_id

        return data

    @staticmethod
    def _validate_created_at(data):

        created_at = data.get("created_at")
        if not created_at:
            raise PydanticCustomError("invalid_created_at", "No created_at found in the message.")

        data["created_at"] = TimeUtilities.convert_epoch_to_ms(created_at)

        return data
    
    @staticmethod
    def _validate_reactions(data):

        reactions_data = data.get("reactions")
        if reactions_data:
            data["reactions"] = ReactionModel(**reactions_data, community_id=data.get("community_id"))

        return data

    @classmethod
    @model_validator(mode="before")
    def _validate_before(cls, data):
        data = cls._validate_state(data)
        data = cls._validate_user(data)
        data = cls._validate_chatroom_id(data)
        data = cls._validate_attachments(data)
        data = cls._validate_replied_conversation_id(data)
        data = cls._validate_created_at(data)
        data = cls._validate_reactions(data)
        data = AttachmentModel._validate_thumbnail_urls(data)

        return data

    @staticmethod
    def _populate_polls(data):

        poll_data = data.get("poll")

        if poll_data:
            data["state"] = conversation_states.CONVERSATION_POLL

            if poll_data.get("title"):
                data["message"] = poll_data.get("title")

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
            else:
                #TODO: Fetch poll options from API and update the data
                pass

            if poll_data.get("allow_multiple_votes"):
                data["multiple_select_state"] = multi_select_poll_states.AT_MAX
                data["multiple_select_no"] = len(poll_data.get("options"))

            if poll_data.get("allow_user_suggestion"):
                data["allow_add_option"] = True

        return data

    @staticmethod
    def _populate_mentions(data):

        if data.get("mentioned_users"):

            mentioned_user_lm_routes = []
            for user in data.get("mentioned_users"):
                user_id = user.get("user_id")
                if not user_id:
                    raise PydanticCustomError(
                        "invalid_user_id", "No user id found in the mentioned users."
                    )

                user_name = user.get("nickname")
                if not user_name:
                    raise PydanticCustomError(
                        "invalid_user_name",
                        "No user name found in the mentioned users.",
                    )

                # Using user_id as uuid to create user mention route
                user_mention_route = USER_PROFILE_ROUTE.format(user_name, user_id)
                mentioned_user_lm_routes.append(user_mention_route)

            # Replace all 'SYMBOL' in the message with the mentioned users
            text = MessageUtilites.replace_mentions(data.get('text'), mentioned_user_lm_routes)
            data['text'] = text

        return data

    @staticmethod
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
                            raise PydanticCustomError("invalid_replied_conversation_id", "No replied conversation id found in the cache.")
                        
                        data["replied_conversation_id"] = lm_id

                type = metadata.get("type")
                if type == "multi-media":
                    
                    attachments = metadata.get("metaData")
                    if attachments:

                        lm_attachments = []
                        index = len(data["attachments"]) + 1

                        user_id = data.get("user_id")
                        chatroom_id = data.get("chatroom_id")

                        if not user_id or not chatroom_id:
                            print(f"No user user_id or chatroom id found in the message data: {data}")
                            return data

                        for _, attachment in enumerate(attachments):
                            lm_attachments.append(AttachmentModel(**attachment, index=index, user_id=user_id, chatroom_id=chatroom_id))
                            index += 1

                        data["attachments"].extend(lm_attachments)

            except json.JSONDecodeError:
                raise PydanticCustomError("invalid_metadata", "Invalid metadata found in the message.")

        return data

    @staticmethod
    def _populate_misfits_attachment_meta(data):

        attachments = data.get('attachments')
        for attachment in attachments:
            if attachment.get('attachment_message'):
                data["text"] = attachment.get('attachment_message')
            
            if attachment.get('replied_conversation_id'):
                data["replied_conversation_id"] = attachment.get('replied_conversation_id')

        return data

    @classmethod
    @model_validator(mode="after")
    def _validate_after(cls, data):
        data = cls._populate_polls(data)
        data = cls._populate_mentions(data)

        data = cls._populate_misfits_metadata(data)
        data = cls._populate_misfits_attachment_meta(data)
        
        return data


class Messages(BaseModel):
    messages: List[MessageModel]
