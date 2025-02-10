import json
import traceback

from typing import List, Optional
from pydantic import BaseModel, Field, model_validator, ValidationError

from pydantic_core import PydanticCustomError

from ..utils.lambda_utilities import LambdaUtilities
from ..utils.migration_utils import MigrationUtils
from ..constants import USER_PROFILE_ROUTE

from utility.states import conversation_states, multi_select_poll_states, attachment_types
from external_services.caching.cache_impl import CacheImpl

from external_services.logging.logging_wrapper import LoggingWrapper

info_logger = LoggingWrapper.get_instance()
error_logger = LoggingWrapper.get_instance()


class AttachmentModel(BaseModel):
    url: str = ""
    type: str = ""
    name: str = ""
    index: int = 0
    thumbnail_url: str = ""
    height: int = None
    width: int = None

    user_id: int = 0
    chatroom_id: int = 0
    community_id: int = 0
    sendbird_api_token: str = ""

    attachment_message: str = ""
    replied_conversation_id: int = 0
    sendbird_parent_msg_id: int = 0

    @staticmethod
    def _validate_file_name(data):

        if data.get('file_name'):
            data["name"] = data.get('file_name')

        return data

    @staticmethod
    def _validate_url(data):

        url = data.get('url')
        if url:
            file_path = MigrationUtils.get_file_path_for_conversation_files(
                data.get('chatroom_id'), data.get('user_id'), url)
            attachment_url = LambdaUtilities.migrate_to_s3(
                url, file_path, data.get("sendbird_api_token")
            )
            if attachment_url:
                data["url"] = attachment_url

        return data

    @staticmethod
    def _validate_type(data):

        sendbird_type = data.get("file_type") or data.get("type")
        if not sendbird_type:
            raise PydanticCustomError("invalid_attachment_type", "No attachment type found in the attachment.")

        # Extract the first word after the "/" in the MIME type string
        parts = sendbird_type.split('/')
        if len(parts) > 1:
            main_type = parts[0]
            secondary_type = parts[1]

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
            elif main_type == 'application':
                data["type"] = secondary_type
            else:
                data["type"] = main_type

                info_logger.info(
                    (
                        f"SendbirdMigration | Invalid attachment type found in the attachment. "
                        f"Type: {sendbird_type}, using existing type: {data.get('type')}"
                    )
                )

        return data

    @staticmethod
    def validate_thumbnail_urls(data):

        if data.get('thumbnails'):

            url = data.get('thumbnails')[0].get('url')
            if url:

                file_path = MigrationUtils.get_file_path_for_conversation_files(
                    data.get("chatroom_id"), data.get("user_id"), url
                )
                
                thumbnail_url = LambdaUtilities.migrate_to_s3(
                    url, file_path, data.get("sendbird_api_token")
                )
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

        metadata_type = metadata.get('type')
        if metadata_type:
            if attachment_types.is_valid_attachment_type(metadata_type):
                data["type"] = metadata_type
            else:
                info_logger.info(
                    (
                        f"SendbirdMigration | Invalid attachment type found in the misfits Type: {metadata_type}, "
                        f"using existing type: {data.get('type')}"
                    )
                )

        url = metadata.get('fileUrl')
        if url:
            file_path = MigrationUtils.get_file_path_for_conversation_files(
                metadata.get('chatroom_id'), metadata.get('user_id'), url)
            attachment_url = LambdaUtilities.migrate_to_s3(
                url, file_path, data.get("sendbird_api_token")
            )
            if attachment_url:
                data["url"] = attachment_url

        thumbnail_url = metadata.get('videoThumbnailUrl')
        if thumbnail_url:
            file_path = MigrationUtils.get_file_path_for_conversation_files(
                metadata.get('chatroom_id'), metadata.get('user_id'), thumbnail_url)
            url = LambdaUtilities.migrate_to_s3(
                thumbnail_url, file_path, data.get("sendbird_api_token")
            )
            if url:
                data["thumbnail_url"] = thumbnail_url

        parent_message = metadata.get('parentMessage')
        if parent_message:

            parent_message_id = parent_message.get("message_id")
            if parent_message_id:

                community_id = metadata.get("community_id")
                if not community_id:
                    raise PydanticCustomError("invalid_community_id", "No community id found in the attachment.")

                lm_id = MigrationUtils.get_lm_id_from_sendbird_message_id(parent_message_id, community_id)
                if not lm_id:
                    info_logger.info(
                        (
                            f"SendbirdMigration | No conversation id found in the cache for "
                            f"sendbird message id: {parent_message_id}. Adding it to sendbird_parent_msg_id"
                        )
                    )
                    data["sendbird_parent_msg_id"] = parent_message_id
                else:
                    data["replied_conversation_id"] = lm_id

        return data

    @staticmethod
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
        data = cls.validate_thumbnail_urls(data)
        data = cls._validate_misfits_keys(data, data)

        data = cls._populate_misfits_metadata(data)

        return data


class PollOptionsModel(BaseModel):
    id: int = 0
    text: str = ""
    vote_count: int = 0
    poll_id: int = 0
    created_by: str = ""


class ReactionModel(BaseModel):
    reaction_key: str = Field(alias="key")
    user_ids: List[int] = []
    community_id: int = 0

    @model_validator(mode="before")
    def _validate_user_ids(cls, data):

        users_list = data.get("user_ids")
        if not users_list:
            info_logger.error(
                (
                    f"SendbirdMigration | No user ids found in the reaction for key: {data.get('reaction_key')}"
                )
            )
            return data
        
        lm_user_ids = []
        
        for user_id in users_list:

            community_id = data.get("community_id")
            if not community_id:
                raise PydanticCustomError("invalid_community_id", "No community id found in the reaction.")

            lm_user_id = MigrationUtils.get_lm_user_id_from_sendbird_user_id(user_id, community_id)
            if not lm_user_id:
                info_logger.error(
                    (
                        f"SendbirdMigration | No user id found in the cache for sendbird user id: {user_id} "
                        f"for reaction key: {data.get('reaction_key')}"
                    )
                )
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

    sendbird_parent_msg_id: int = 0
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
    poll_type: int = 2  # Default poll type is 2 (Open Poll)
    expiry_time: int = 0
    no_poll_expiry: bool = True
    allow_add_option: bool = False
    multiple_select_state: Optional[int] = Field(default=None)
    multiple_select_no: Optional[int] = Field(default=0)

    reactions: List[ReactionModel] = []

    sendbird_api_token: str = ""

    @staticmethod
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
        lm_user_id = MigrationUtils.get_lm_user_id_from_sendbird_user_id(user_id, community_id)
        if not lm_user_id:
            raise PydanticCustomError("invalid_user_id", "No user id found in the cache.")

        data["user_id"] = lm_user_id

        return data

    @staticmethod
    def _validate_message(data):

        if data.get("message"):
            data["text"] = data.get("message")

        return data

    @staticmethod
    def _validate_chatroom_id(data):

        # Fetch chatroom_id
        channel_url = data.get("channel_url")
        if not channel_url:
            raise PydanticCustomError("invalid_chatroom_id", "No chatroom id found in the message.")

        community_id = data.get("community_id")
        if not community_id:
            raise PydanticCustomError("invalid_community_id", "No community id found in the message.")

        # Fetch likeminds chatroom_id from cache
        lm_chatroom_id = MigrationUtils.get_lm_chatroom_id_from_sendbird_channel_id(channel_url, community_id)
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
                info_logger.error(
                        (
                            f"SendbirdMigration | No user user_id or chatroom id found in the message data: {data}"
                        )
                    )
                return data

            if file_data:
                file_data["index"] = len(data["attachments"]) + 1
                file_data["user_id"] = user_id
                file_data["chatroom_id"] = chatroom_id
                file_data["sendbird_api_token"] = data.get("sendbird_api_token")

                data["attachments"].append(AttachmentModel(**file_data))

                return data

            if files_data:
                for index, file_data in enumerate(files_data):
                    file_data["index"] = index
                    file_data["user_id"] = user_id
                    file_data["chatroom_id"] = chatroom_id
                    file_data["sendbird_api_token"] = data.get("sendbird_api_token")

                    data["attachments"].append(AttachmentModel(**file_data))

        return data

    @staticmethod
    def _validate_parent_message_id(data):

        parent_message_id = data.get("parent_message_id")
        if parent_message_id:

            community_id = data.get("community_id")
            if not community_id:
                raise PydanticCustomError("invalid_community_id", "No community id found in the message.")

            # Fetch LM conversation_id from cache
            conversation_id = MigrationUtils.get_lm_id_from_sendbird_message_id(
                parent_message_id, community_id
            )
            if not conversation_id:
                info_logger.info(
                    (
                        f"SendbirdMigration | No conversation id found in the cache for sendbird message id: "
                        f"{data.get('replied_conversation_id')}. Adding it to sendbird_parent_msg_id"
                    )
                )
                data["sendbird_parent_msg_id"] = parent_message_id
            else:
                data["replied_conversation_id"] = conversation_id

        return data

    @staticmethod
    def _validate_created_at(data):

        created_at = data.get("created_at")
        if not created_at:
            raise PydanticCustomError("invalid_created_at", "No created_at found in the message.")

        data["created_at"] = MigrationUtils.ensure_epoch_in_ms(created_at)

        return data

    @staticmethod
    def _validate_reactions(data):

        reactions_data = data.get("reactions")
        if reactions_data:
            reactions_list = []
            for reaction in reactions_data:
                reaction["community_id"] = data.get("community_id")
                reactions = ReactionModel(**reaction)
                reactions_list.append(reactions)

            data["reactions"] = reactions_list

        return data

    @staticmethod
    def _populate_polls(data):

        poll_data = data.get("poll")

        if poll_data:
            data["state"] = conversation_states.CONVERSATION_POLL

            if poll_data.get("title"):
                data["text"] = poll_data.get("title")

            if poll_data.get("close_at") and poll_data.get("close_at") > 0:
                data["expiry_time"] = MigrationUtils.ensure_epoch_in_ms(poll_data.get("close_at"))
                data["no_poll_expiry"] = False

            if poll_data.get("options"):
                data["polls"] = [
                    PollOptionsModel(**poll_option) for poll_option in poll_data.get("options")
                ]

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

                lm_user_id = MigrationUtils.get_lm_user_id_from_sendbird_user_id(user_id, data.get("community_id"))

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
            message = MigrationUtils.replace_mentions(data.get("text"), mentioned_user_lm_routes)
            data["text"] = message

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

                        lm_id = MigrationUtils.get_lm_id_from_sendbird_message_id(parent_message_id, community_id)
                        if not lm_id:
                            info_logger.info(
                                (
                                    f"SendbirdMigration | No conversation id found in the cache for "
                                    f"sendbird message id: {parent_message_id}. Adding it to sendbird_parent_msg_id"
                                )
                            )
                            data["sendbird_parent_msg_id"] = parent_message_id
                        else:
                            data["replied_conversation_id"] = lm_id

                media_type = metadata.get("type")
                if media_type == "multi-media":

                    data["text"] = "" # Set text to blank, as multi-media messages don't have text

                    attachments = metadata.get("metaData")
                    if attachments:

                        lm_attachments = []
                        index = len(data.get("attachments", [])) if data.get("attachments") else 0

                        user_id = data.get("user_id")
                        chatroom_id = data.get("chatroom_id")

                        if not user_id or not chatroom_id:
                            info_logger.error(
                                (
                                    f"SendbirdMigration | No user user_id or chatroom id found in the " 
                                    f"message data: {data}"
                                )
                            )
                            return data

                        for _, attachment in enumerate(attachments):
                            attachment["index"] = index
                            attachment["user_id"] = user_id
                            attachment["chatroom_id"] = chatroom_id
                            attachment["sendbird_api_token"] = data.get("sendbird_api_token")

                            lm_attachments.append(AttachmentModel(**attachment))
                            index += 1

                        data["attachments"] = lm_attachments

            except json.JSONDecodeError:
                raise PydanticCustomError("invalid_metadata", "Invalid metadata found in the message.")

        return data

    @staticmethod
    def _populate_misfits_attachment_meta(data):

        attachments = data.get('attachments', [])
        for attachment in attachments:
            if attachment.attachment_message:
                data["text"] = attachment.attachment_message if not attachment.attachment_message == "file" \
                    else data.get("text")

            if attachment.replied_conversation_id:
                data["replied_conversation_id"] = attachment.replied_conversation_id

            if attachment.sendbird_parent_msg_id:
                data["sendbird_parent_msg_id"] = attachment.sendbird_parent_msg_id

        return data

    @model_validator(mode="before")
    def _validate_before(cls, data):

        data = cls._validate_state(data)
        data = cls._validate_user(data)
        data = cls._validate_message(data)
        data = cls._validate_chatroom_id(data)
        data = cls._validate_attachments(data)
        data = cls._validate_parent_message_id(data)
        data = cls._validate_created_at(data)
        data = cls._validate_reactions(data)
        data = AttachmentModel.validate_thumbnail_urls(data)

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
                    info_logger.info(
                        (
                            f"SendbirdMigration | Skipping ADMM (Admin) message {message.get('message_id')}"
                        )
                    )
                    continue

                validated_message = MessageModel(**message)
                validated_messages.append(validated_message)

            except ValidationError as e:
                info_logger.error(
                    (
                        f"SendbirdMigration | Validation error for message_id: {message.get('message_id')} "
                        f"| Exception: {e} | Traceback: {traceback.format_exc()}"
                    )
                )
                continue

            except Exception as e:
                info_logger.error(
                    (
                        f"SendbirdMigration | Unexpected error for message {message.get('message_id')} "
                        f"Error: {e} | Traceback: {traceback.format_exc()}"
                    )
                )
                continue

        values['messages'] = validated_messages
        return values
