SDK_USER_INITIATE_COMMUNITY_DATA = "sdk_user_initiate_community_%s"
SDK_USER_INITIATE_COMMUNITY_DATA_TIMEOUT = 86400  # in seconds, = 24 hours

CONVERSATION_POLL_OPTIONS_CONVERSATION_ID = "conversation_poll_options_%s"
CONVERSATION_POLL_VOTERS_CONVERSATION_ID = "conversation_poll_voters_%s"
CONVERSATION_COMMUNITY_PREVIEW = "COMMUNITY_PREVIEW_%s_%s"

CHATROOM_REACTIONS_CACHE_KEY = "chatroom_reaction_%s"
CONVERSATION_REACTIONS_CACHE_KEY = "conversation_reaction_%s"

EVENT_INSTRUCTORS_CHATROOM = "event_instructors_%s"
EVENT_HIGHLIGHTS_CHATROOM = "event_highlights_%s"
EVENT_MEMBERTESTIMONIALS_CHATROOM = "event_membertestimonials_%s"
EVENT_FAQ_CHATROOM = "event_faq_%s"
EVENT_ATTENDEES_CHATROOM = "event_attendees_%s"

EVENT_ATTENDEES_CONVERSATION = "event_attendees_%s"

CHATROOM_PARTICIPANTS_CREATED_CACHE_KEY = "chatroom_participants_created_{}"

INTERNATIONAL_OTP_GENERATE_CACHE_KEY = "international_otp_generate_%s"

COMMUNITY_PINNED_CHATROOMS_LIST_CACHE_KEY = "pin_chatrooms_list_{}"

CHATROOM_TYPE_CONVERSION = "chatroom_type_conversion_{}"

SYNC_LJ_MIN_TIMESTAMP = "sync_data_{}_{}"

SWARM_CACHE_KEY_CONFIGURATIONS = "%s_community_configurations"

WIDGET_CONFIGURATIONS_CACHE_KEY = "{}_widget_configurations"
SWARM_CACHE_KEY_WEBHOOKS = "%s_webhooks"
SWARM_TOP_LIKED_COMMENTS_CACHE_KEY = "{}_*_top_liked_comments"

KETTLE_CACHE_KEY_COMMUNITY_SETTINGS = "{}_community_settings" # community_id
KETTLE_CACHE_KEY_USER_META = "{}_{}_user_meta" # community_id, user_unique_id
KETTLE_CACHE_KEY_PROFILE_META_CONFIGURATIONS = "{}_profile_meta_configurations" # community_id
KETTLE_CACHE_KEY_FEED_SETTINGS_CONFIGURATIONS = "{}_feed_settings_configurations"  # community_id
KETTLE_CACHE_KEY_FEED_META_CONFIGURATIONS = "{}_feed_metadata_configurations"  # community_id
KETTLE_CACHE_KEY_WIDGET_META = "{}_{}_widget_meta" # community_id, widget_id
KETTLE_CACHE_KEY_ANONYMOUS_USER_META = "{}_lm-anonymous-user_user_meta"  # community_id

SWARM_CACHE_KEY_COMMUNITY_SETTINGS = "{}_community_settings" # community_id
SWARM_CACHE_KEY_USER_COMMUNITY_CHANNELS = "{}_{}_user_community_channels" # community_id, user_unique_id

CHATBOT_ASSISTANT_THREAD_CACHE_KEY = "{}_{}_chatbot_threads" # chatroom_id, assistant_id
SWARM_CACHE_KEY_BLOCK_USER = "{}_{}_blocked_users" # community_id, user_unique_id
KETTLE_CACHE_CHATROOM_PARTICIPANTS = "chatroom_participants_{}" # chatroom_participants_<chatroom_id>

SWARM_CACHE_KEY_TOP_COMMENTS = "{}_*_top_liked_comments" # community_id

SENDBIRD_MIGRATION_CHANNEL_MAP_CACHE_KEY = "sendbird_migration_{}_{}"
