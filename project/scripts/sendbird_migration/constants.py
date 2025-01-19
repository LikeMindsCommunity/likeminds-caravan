# Older Migration Class - To be used when exporting using APIs
APPLICATION_ID = "A7128051-8508-46A1-B4A2-821886B5781F"

LIKEMINDS_API_KEY = "35fdd780-499f-4948-a87d-cf7502948314"
PLATFORM_CODE = "web"
PLATFORM_TYPE = "dashboard"
VERSION_CODE = 26

TTL_FOR_CACHE = 60 * 60 * 60

JSON_FILE_TYPE = ".json"

# S3 Paths for Media files
USER_PROFILE_IMAGE_S3_PATH = "files/profile/{}/{}-{}"
CHATROOM_IMAGE_S3_PATH = "files/chatroom/image/{}"
CONVERATION_FILE_S3_PATH = "files/collabcard/{}/conversation/{}/" # Chatroom ID, user_id
DEFAULT_FILE_S3_PATH = "files/"

LAMBDA_URL = "https://mcm23vgasphq26jbnp4xwtkeku0qkhzb.lambda-url.ap-south-1.on.aws/"  # Hosted on old AWS account

USER_PROFILE_ROUTE = "<<[{}]|route://user_profile/[{}]>>" # NAME, USER_ID

MENTIONED_USERS_SYMBOL = "∞" # Misfits symbol for mentioned users

# Cache Keys for Mapping Sendbird -> Likeminds IDs
SENDBIRD_CHANNEL_MAP_KEY = "sendbird_migration_channel_{}" # sendbird chatroom_id -> likeminds chatroom_id
SENDBIRD_USER_MAP_KEY = "sendbird_user_{}" # sendbird user_id -> likeminds user_id
SENDBIRD_MESSAGE_MAP_KEY = "sendbird_message_{}" # sendbird message_id -> likeminds conversation_id
