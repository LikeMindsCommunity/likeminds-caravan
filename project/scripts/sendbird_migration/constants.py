# Constants for Sendbird Migration (Older)
APPLICATION_ID = "A7128051-8508-46A1-B4A2-821886B5781F"
API_TOKEN = "441ddd489a87926711df7e8e6c473af1fca1c532"
LIKEMINDS_API_KEY = "35fdd780-499f-4948-a87d-cf7502948314"
PLATFORM_CODE = "web"
PLATFORM_TYPE = "dashboard"
VERSION_CODE = 26

# Sendbird Endpoints
SENDBIRD_API_BASE_URL = "https://api-{}.sendbird.com/v3"
LIST_USERS_ENDPOINT = "{base_url}/users"
LIST_CHANNELS_ENDPOINT = "{base_url}/{channel_type}"
LIST_MESSAGES_ENDPOINT = "{base_url}/{channel_type}/{channel_url}/messages"
LIST_POLL_OPTIONS = "{base_url}/polls/{poll_id}"
LIST_POLL_VOTERS_ENDPOINT = "{base_url}/polls/{poll_id}/options/{poll_option_id}/voters"

# Sendbird Enpoint Types
ENDPOINT_TYPE_LIST_USERS = "list_users"
ENDPOINT_TYPE_LIST_CHANNELS = "list_channels"
ENDPOINT_TYPE_LIST_MESSAGES = "list_messages"
ENDPOINT_TYPE_LIST_POLL_OPTIONS = "list_poll_options"
ENDPOINT_TYPE_LIST_POLL_VOTERS = "list_poll_voters"

# Sendbird Channel Types
OPEN_CHANNELS_TYPE = "open_channels"
GROUP_CHANNELS_TYPE = "group_channels"

# S3 Paths for Media files
USER_PROFILE_IMAGE_S3_PATH = "files/profile/{}/{}-{}"
CHATROOM_IMAGE_S3_PATH = "files/chatroom/image/{}"
CONVERSATION_FILE_S3_PATH = "files/collabcard/{}/conversation/{}/"  # Chatroom ID, user_id
DEFAULT_FILE_S3_PATH = "files/"

# Lambda URL for Migrating Files to Likeminds S3
LAMBDA_URL = "https://mcm23vgasphq26jbnp4xwtkeku0qkhzb.lambda-url.ap-south-1.on.aws/"  # Hosted on old AWS account

# TTL for Sendbird -> LM ID Mapping Cache
TTL_FOR_CACHE = 60 * 60 * 60

# Cache Keys for Mapping Sendbird -> Likeminds IDs
SENDBIRD_CHANNEL_MAP_KEY = "sendbird_migration_channel_{}_{}"  # community_id, sendbird_channel_id
SENDBIRD_USER_MAP_KEY = "sendbird_user_{}_{}"  # community_id, sendbird_user_id
SENDBIRD_MESSAGE_MAP_KEY = "sendbird_message_{}_{}"  # community_id, sendbird_message_id

JSON_FILE_TYPE = ".json"

USER_PROFILE_ROUTE = "<<[{}]|route://user_profile/[{}]>>"  # NAME, USER_ID

MENTIONED_USERS_SYMBOL = "∞"  # Misfits symbol for mentioned users
