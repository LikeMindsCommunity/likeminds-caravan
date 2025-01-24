# Constants for Sendbird Migration (Older)
LIKEMINDS_API_KEY = "<LIKEMINDS_API_KEY>"
PLATFORM_CODE = "web"
VERSION_CODE = 26

# Sendbird Endpoints
SENDBIRD_API_BASE_URL = "https://api-{}.sendbird.com/v3"
LIST_USERS_ENDPOINT = "{}/users"
LIST_CHANNELS_ENDPOINT = "{}/{}"
LIST_OPEN_CHANNEL_PARTICIPANTS_ENDPOINT = "{}/open_channels/{}/participants"
LIST_MESSAGES_ENDPOINT = "{}/{}/{}/messages"
LIST_POLL_OPTIONS = "{}/polls/{}"
LIST_POLL_VOTERS_ENDPOINT = "{}/polls/{}/options/{}/voters"

# Sendbird Enpoint Types
ENDPOINT_TYPE_LIST_USERS = "list_users"
ENDPOINT_TYPE_LIST_CHANNELS = "list_channels"
ENDPOINT_TYPE_LIST_MESSAGES = "list_messages"
ENDPOINT_TYPE_LIST_POLL_OPTIONS = "list_poll_options"
ENDPOINT_TYPE_LIST_POLL_VOTERS = "list_poll_voters"
ENDPOINT_TYPE_LIST_OPEN_CHANNEL_PARTICIPANTS = "list_open_channel_participants"

# Sendbird Channel Types
OPEN_CHANNELS_TYPE = "open_channels"
GROUP_CHANNELS_TYPE = "group_channels"

# S3 Paths for Media files
USER_PROFILE_IMAGE_S3_PATH = "files/profile/{}/{}-{}"
CHATROOM_IMAGE_S3_PATH = "files/chatroom/image/{}"
CONVERSATION_FILE_S3_PATH = "files/collabcard/{}/conversation/{}/"  # Chatroom ID, user_id
DEFAULT_FILE_S3_PATH = "files/"

# TTL for Sendbird -> LM ID Mapping Cache
TTL_FOR_CACHE = 60 * 60 * 60

# Cache Keys for Mapping Sendbird -> Likeminds IDs
SENDBIRD_CHANNEL_MAP_KEY = "sendbird_migration_{}_channel_{}"  # community_id, sendbird_channel_id
SENDBIRD_USER_MAP_KEY = "sendbird_migration_{}_user_{}"  # community_id, sendbird_user_id
SENDBIRD_MESSAGE_MAP_KEY = "sendbird_migration_{}_message_{}"  # community_id, sendbird_message_id

JSON_FILE_TYPE = ".json"

USER_PROFILE_ROUTE = "<<[{}]|route://user_profile/[{}]>>"  # NAME, USER_ID

MENTIONED_USERS_SYMBOL = "∞"  # Misfits symbol for mentioned users
