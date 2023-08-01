import enum


class PlatformCodes:
    ANDROID = "an"
    IOS = "ios"
    WEB = 'web'
    WEB_MOBILE = "web-mobile"
    WEB_DESKTOP = "web-desktop"

    PALTFORM_CODE_LIST = [ANDROID, IOS, WEB, WEB_MOBILE, WEB_DESKTOP]


platform_codes = PlatformCodes()


class ManagerRights:
    MANAGER_RIGHT_DELETE_ROOMS = 0
    MANAGER_RIGHT_APPROVE_REMOVE_MEMBERS = 1
    MANAGER_RIGHT_EDIT_COMMUNITY = 2
    MANAGER_RIGHT_VIEW_CONTACT_INFO = 3
    MANAGER_RIGHT_ADD_MANAGERS = 4
    MODERATE_DM_SETTINGS = 5
    MODERATE_FEED_AND_COMMENTS = 6
    MANAGER_RIGHT_DELETE_ROOMS_TITLE = "Moderate chatrooms"
    MANAGER_RIGHT_APPROVE_MEMBERS_TITLE = "Moderate members"
    MANAGER_RIGHT_EDIT_COMMUNITY_TITLE = "Edit community details"
    MANAGER_RIGHT_VIEW_CONTACT_INFO_TITLE = "View member contact info"
    MANAGER_RIGHT_ADD_MANAGERS_TITLE = "Add community managers"
    MODERATE_DM_SETTINGS_TITLE = "Moderate DM settings"
    MODERATE_FEED_AND_COMMENTS_TITLE = "Moderate feed and comments"

    DEFAULT_MANAGER_RIGHTS = [MANAGER_RIGHT_DELETE_ROOMS, MANAGER_RIGHT_APPROVE_REMOVE_MEMBERS,
                              MANAGER_RIGHT_EDIT_COMMUNITY]
    ALL_MANAGER_RIGHTS = [MANAGER_RIGHT_DELETE_ROOMS, MANAGER_RIGHT_APPROVE_REMOVE_MEMBERS,
                          MANAGER_RIGHT_EDIT_COMMUNITY, MANAGER_RIGHT_VIEW_CONTACT_INFO,
                          MANAGER_RIGHT_ADD_MANAGERS, MODERATE_DM_SETTINGS, MODERATE_FEED_AND_COMMENTS]


manager_rights = ManagerRights()


class MemberRights:
    MEMBER_RIGHT_CREATE_ROOMS = 0
    MEMBER_RIGHT_CREATE_POLL = 1
    MEMBER_RIGHT_CREATE_EVENT = 2
    MEMBER_RIGHT_RESPOND_IN_ROOM = 3
    MEMBER_RIGHT_INVITE_PRIVATE_LINK = 4
    MEMBER_RIGHT_AUTO_APPROVE = 5
    MEMBER_RIGHT_CREATE_SECRET_ROOM = 6
    MANAGER_RIGHT_ENABLE_DIRECT_MESSAGES = 7
    MEMBER_RIGHT_ENABLE_MEMBERS_CAN_DM = 8
    MEMBER_RIGHT_CREATE_POSTS = 9
    MEMBER_RIGHT_COMMENT_AND_REPLY_ON_POSTS = 10

    MEMBER_RIGHT_CREATE_ROOMS_TITLE = "Create chat rooms"
    MEMBER_RIGHT_CREATE_POLL_TITLE = "Create polls"
    MEMBER_RIGHT_CREATE_EVENT_TITLE = "Create events"
    MEMBER_RIGHT_RESPOND_IN_ROOM_TITLE = "Respond in chat rooms"
    MEMBER_RIGHT_INVITE_PRIVATE_LINK_TITLE = "Invite members via private link"
    MEMBER_RIGHT_AUTO_APPROVE_TITLE = "Auto-approve created chat rooms"
    MEMBER_RIGHT_CREATE_SECRET_CHATROOM_TITLE = "Create secret chatroom"
    MANAGER_RIGHT_ENABLE_DIRECT_MESSAGES_TITLE = "Direct messages"
    MEMBER_RIGHT_ENABLE_MEMBERS_CAN_DM_TITLE = "Members who can initiate DMs"
    MEMBER_RIGHT_CREATE_POSTS_TITLE = "Create posts"
    MEMBER_RIGHT_COMMENT_AND_REPLY_ON_POSTS_TITLE = "Comment and reply on posts"

    DEFAULT_MEMBER_RIGHTS = [MEMBER_RIGHT_CREATE_ROOMS, MEMBER_RIGHT_CREATE_POLL,
                             MEMBER_RIGHT_CREATE_EVENT, MEMBER_RIGHT_RESPOND_IN_ROOM,
                             MEMBER_RIGHT_AUTO_APPROVE]
    ALL_MEMBER_RIGHTS = [MEMBER_RIGHT_CREATE_ROOMS, MEMBER_RIGHT_CREATE_POLL,
                         MEMBER_RIGHT_CREATE_EVENT, MEMBER_RIGHT_RESPOND_IN_ROOM,
                         MEMBER_RIGHT_INVITE_PRIVATE_LINK, MEMBER_RIGHT_AUTO_APPROVE,
                         MEMBER_RIGHT_CREATE_SECRET_ROOM]


member_rights = MemberRights()


class ModerationHistoryTypes:
    APPLIED_PUBLIC_LINK = 0
    APPLIED_PRIVATE_LINK = 1
    APPROVED_FROM = 2
    MEMBER_PERMISSION_EDITED = 3
    MANAGER_PERMISSION_EDITED = 4
    MADE_COMMUNITY_MANAGER = 5
    REMOVED_AS_COMMUNITY_MANAGER = 6
    REMOVED_FROM_COMMUNITY = 7
    LEFT_COMMUNITY = 8
    STARTED_COMMUNITY = 9
    TRANSFERRED_OWNERSHIP = 10
    REJOINED_COMMUNITY_PUBLIC_LINK = 11
    REJOINED_COMMUNITY_PRIVATE_LINK = 12
    APPLIED_PUBLIC_LINK_WEBSITE = 13
    SDK_JOIN = 14
    SDK_PENDING_MEMBER = 15
    SDK_REJOINED_MEMBER = 16
    APPLIED_PUBLIC_LINK_TEXT = "Applied via invite link from "
    APPLIED_PRIVATE_LINK_TEXT = "Joined via invite link from "
    APPROVED_FROM_TEXT = "Approved from "
    MEMBER_PERMISSION_EDITED_TEXT = "Member permission edited by "
    MANAGER_PERMISSION_EDITED_TEXT = "Management permission edited by "
    MADE_COMMUNITY_MANAGER_TEXT = "Made community manager by "
    REMOVED_AS_COMMUNITY_MANAGER_TEXT = "Removed as community manager by "
    REMOVED_MEMBER_FROM_COMMUNITY_TEXT = "Removed from community by "
    LEFT_COMMUNITY_TEXT = "Left community"
    STARTED_COMMUNITY_TEXT = "Started this community"
    TRANSFERRED_OWNERSHIP_TEXT = "Transferred ownership to "
    REJOINED_COMMUNITY_PUBLIC_LINK_TEXT = "Rejoined via invite link from  "
    REJOINED_COMMUNITY_PRIVATE_LINK_TEXT = "Rejoined via invite link from "
    APPLIED_PUBLIC_LINK_WEBSITE_TEXT = "Applied via community website"
    SDK_JOIN_MEMBER_TEXT = "{} joined the community"
    SDK_PENDING_MEMBER_TEXT = "Becomes pending member of community"


moderation_history_types = ModerationHistoryTypes()


class ReportActionTypes:
    EDIT_MEMBER_PERMISSION = 0
    REMOVE_FROM_COMMUNITY = 1
    LEFT_THE_COMMUNITY = 2
    RESPONSE_DELETED_BY_CM = 3
    RESPONSE_DELETED_BY_CREATOR = 4
    CHATROOM_DELETED_BY_CM = 5
    CHATROOM_DELETED_BY_CREATOR = 6


report_Action_Types = ReportActionTypes()


class ReportTypes:
    REPORT_MEMBER = 0
    REPORT_CHATROOM = 1
    REPORT_CONVERSATION = 2
    REPORT_COMMUNITY = 3
    REPORT_LINK = 4
    REPORT_POST = 5
    REPORT_COMMENT = 6
    REPORT_REPLY = 7


report_Types = ReportTypes()


# tag types for reports
class ReportTagTypes:
    CHATROOM_REPORT_TAG = 0
    MEMBER_REPORT_TAG = 1
    COMMUNITY_REPORT_TAG = 2
    CONVERSATION_REPORT_TAG = 3
    LINK_REPORT_TAG = 4


report_Tag_Types = ReportTagTypes()


# chatroom actions
class ChatroomActions:
    ACTION_RENAME = 1
    ACTION_VIEW_PARTICIPANTS = 2
    ACTION_INVITE = 3
    ACTION_JOIN_CHATROOM = 4
    ACTION_VIEW_COMMUNITY = 5
    ACTION_MUTE = 6
    ACTION_DELETE = 7
    ACTION_UNMUTE = 8
    ACTION_UNFOLLOW = 9
    ACTION_REPORT = 10
    ACTION_MARK_ACTIVE = 11
    ACTION_MARK_INACTIVE = 12
    ACTION_PIN_CHATROOM = 13
    ACTION_UNPIN_CHATROOM = 14
    ACTION_LEAVE_CHATROOM = 15
    ACTION_ADD_ALL_MEMBERS = 16
    ACTION_SETTINGS = 17
    ACTION_MEMBER_CAN_MESSAGE = 18
    ACTION_ACCESSIBLE_WITHOUT_SUBSCRIPTION = 19


chatroom_actions = ChatroomActions()


# collabcard stats
class CollabcardTypes:
    CARD_NORMAL = 0
    CARD_INTRO = 1
    CARD_EVENT = 2
    CARD_POLL = 3
    CARD_FEEDBACK = 4
    CARD_HIDDEN = 4
    CARD_PUBLIC_EVENT = 6
    CARD_PURPOSE = 7
    CARD_MASTER_INTRO = 9
    CARD_DIRECT_MESSAGE = 10
    CARD_FEED_GROUP = 11


card_types = CollabcardTypes()


class CollabcardStates:
    COLLABCARD_STATE_UNSEEN = 0
    COLLABCARD_STATE_SEEN = 1
    COLLABCARD_STATE_FOLLOW = 2

    COLLABCARD_STATE_UNATTEND_FOLLOWING = COLLABCARD_STATE_FOLLOW
    COLLABCARD_STATE_ATTEND_FOLLOWING = 3
    COLLABCARD_STATE_ATTENDING = 3
    COLLABCARD_STATE_ATTEND_UNFOLLOWING = 4


collabcard_states = CollabcardStates()


class PollTypes:
    POLL_TYPE_INSTANT = 0
    POLL_TYPE_DEFERRED = 1


poll_types = PollTypes()


class MultiSelectPollStates:
    # class to save states of multiple select poll
    EXACTLY = 0
    AT_MAX = 1
    AT_MOST = 1
    AT_LEAST = 2


multi_select_poll_states = MultiSelectPollStates()


# member state
class MemberStates:
    GUEST = 0

    ADMIN = 1
    TEMP_ADMIN = 2
    PENDING_MEMBER = 3
    MEMBER = 4
    DECLINED_MEMBER = 5
    UNKNOWN_NOMINATED_PROMOTER = 6
    KNOWN_NOMINATED_PROMOTER = 7
    INTERESTED_MEMBER = 8
    PROFILE_UNAVAILABLE = 9


member_states = MemberStates()


class DeletedMembers:
    LEFT = 0
    REMOVED = 1
    MEMBERSHIP_EXPIRED = 2


deleted_members = DeletedMembers()


class QuestionStates:
    TEXT = 0
    CHOICE_SINGLE = 1
    CHOICE_MULTIPLE = 2
    TEXT_WITH_LIMIT = 3
    PARAGRAPH = 4
    FILE_UPLOAD = 5
    DATE_TIME = 6
    INTRODUCTION = 7
    PROFILE_LINK = 8
    MOBILE_NO = 9
    EMAIL_ID = 10
    GOOGLE_CITY_FETCH = 11
    NAME = 12


question_states = QuestionStates()


class CommunityStates:
    PRIVATE = 0
    HIDDEN = 1
    DELETED = 2
    PILOT = 3
    PILOT_ACTIVE = 4
    WHATSAPP = 5


community_states = CommunityStates()


class EmailStates:
    NON_PRIMARY = 0
    PRIMARY = 1


email_states = EmailStates()


class PhoneStates:
    NON_PRIMARY = 0
    PRIMARY = 1


mobile_states = PhoneStates()


class CommunityLevelsState:
    PENDING = 0
    COMPLETE = 1
    LOCKED = 2


community_level_states = CommunityLevelsState()


class ClickState:
    DEFAULT = 0
    SET_COMMUNITY = 1
    PENDING_APPROVAL = 2

    SET_PURPOSE = 3
    SKIP_COMMUNITY = 4


click_states = ClickState()


class LevelClickStates:
    DEFAULT = 0
    DIRECTORY_CREATED = 1
    COMMUNITY_JOINED = 2


level_click_states = LevelClickStates()


class HomeSnackbarType(enum.Enum):
    REMOVED_MEMBER = 1
    CHATROOM_DELETED_BY_CREATOR = 2
    CHATROOM_DELETED_BY_COMMUNITY_MANAGER = 3
    CHATROOM_REJECTED_BY_COMMUNITY_MANAGER = 4

    @classmethod
    def has_value(cls, value) -> bool:
        response = False
        try:
            if cls.__contains__(value):
                response = True
        except AttributeError as e:
            response = False
        finally:
            return response


class SyncTypes(enum.Enum):
    CONVERSATION = 1
    MEMBERS = 2
    COMMUNITY = 3
    CHATROOM = 4

    @classmethod
    def has_value(cls, value) -> bool:
        response = False
        try:
            if cls.__contains__(value):
                response = True
        except AttributeError as e:
            response = False
        finally:
            return response


class SyncNotificationTypes(enum.Enum):
    SINGLE_MEMBER = 1
    ALL_MEMBERS = 2

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_


class ConversationStates:
    ANSWER = 0
    CONVERSATION_HEADER = 1
    CONVERSATION_FOLLOW = 2
    CONVERSATION_UNFOLLOW = 3
    CONVERSATION_CREATOR = 4
    CONVERSATION_COMMUNITY_EDIT = 5
    CONVERSATION_GUEST = 6

    CONVERSATION_ADD_PARTICIPANT = 7
    CONVERSATION_LEAVE_CHATROOM = 8
    CONVERSATION_REMOVED_FROM_CHATROOM = 9

    CONVERSATION_POLL = 10
    CONVERSATION_ADD_ALL_MEMBERS = 11

    CHATROOM_TOPIC = 12

    CONVERSATION_DIRECT_MESSAGE_MEMBER_REMOVED_OR_LEFT = 13
    CONVERSATION_DIRECT_MESSAGE_CM_REMOVED = 14
    CONVERSATION_DIRECT_MESSAGE_MEMBER_BECOMES_CM_DISABLE_CHAT = 15
    CONVERSATION_DIRECT_MESSAGE_CM_BECOMES_MEMBER_ENABLE_CHAT = 16
    CONVERSATION_DIRECT_MESSAGE_MEMBER_BECOMES_CM_ENABLE_CHAT = 17
    CONVERSATION_EVENT = 18
    CONVERSATION_DIRECT_MESSAGE_BLOCK_MEMBER_DISABLE_CHAT = 19
    CONVERSATION_DIRECT_MESSAGE_UNBLOCK_MEMBER_ENABLE_CHAT = 20


conversation_states = ConversationStates()


class ConversationPollTypes:
    INSTANT = 0
    DEFERRED = 1


conversation_poll_types = ConversationPollTypes()


class SearchIndexes(enum.Enum):
    CHATROOM = "chatroom"
    CONVERSATION = "conversation"
    MEMBER_DIRECTORY = "member_directory"


class LoginTypes:
    GOOGLE = "google"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedIn"
    LINKEDIN_WEB = "linkedin_web"
    APPLE = "apple"
    CUSTOM = "custom"
    SDK = "sdk"


login_types = LoginTypes()


class SubscriptionStatus(enum.Enum):
    ACTIVE = 0
    EXPIRED = 1
    GRACE_PERIOD = 2
    RENEWAL_DUE = 3
    SUBSCRIPTION_NOT_FOUND = 4

    def fetch_name(self):
        return '%s' % (" ".join([word.lower() for word in self.name.split("_")]))


class EventAccess:
    NON_COMMUNITY_USERS = 0
    COMMUNITY_MEMBERS = 1
    NON_COMMUNITY_USERS_AND_MEMBERS = 2


event_access = EventAccess()


class EventWebflowUpdateTypes:
    FILE = 0
    INSTRUCTORS = 1
    HIGHLIGHTS = 2
    TESTIMONIALS = 3
    FAQ = 4
    META = 5


event_webflow_update_types = EventWebflowUpdateTypes()


class CommunitySettingTypes:
    INTRO_ROOM = "intro_room"
    MEMBERS_AUTO_JOIN = "members_auto_join"
    FEED = "feed"
    DIRECT_MESSAGES = "direct_messages"
    MEMBERS_CAN_DM = "members_can_dm"
    DIRECT_MESSAGE_SETTING = "direct_messages_setting"
    DIRECT_MSGS_GROUP_MSGS = "direct_messages_with_group_messages"
    CHATROOMS = "chatrooms"
    SECRET_CHATROOMS_INVITE = "secret_chatrooms_invite"
    POST_GROUPS = "post_groups"
    SECRET_GROUP_INVITE = "secret_groups_invite"
    CREATE_INTRO_ROOMS = "create_intro_rooms"


community_setting_types = CommunitySettingTypes()


class CohortTypes:
    NORMAL = 0
    SUBSCRIPTION_PLAN = 1
    SUBSCRIPTION_EXPIRED_PLAN = 2
    ALL_MEMBER = 3


cohort_types = CohortTypes()

cohort_type_list = [cohort_types.NORMAL, cohort_types.SUBSCRIPTION_PLAN,
                    cohort_types.SUBSCRIPTION_EXPIRED_PLAN, cohort_types.ALL_MEMBER]


class GetStartedTypes:
    CREATE_COMMUNITY_TYPE = 0
    INVITE_MEMBERS_TYPE = 1
    CREATE_EVENT_TYPE = 2
    CUSTOMISE_JOIN_FORM = 3
    JOIN_COMMUNITY_HOOD = 4


get_started_types = GetStartedTypes()

get_started_types_object = {
    "Create community": get_started_types.CREATE_COMMUNITY_TYPE,
    "Invite members": get_started_types.INVITE_MEMBERS_TYPE,
    "Create event": get_started_types.CREATE_EVENT_TYPE
}


class SendInviteTypes:
    EMAIL_INVITE = 'email'
    WHATSAPP_INVITE = 'whatsapp'


send_invite_types = SendInviteTypes()


class UserEmailSendStatusTypes:
    CM_ONBOARDING = 1
    TAGGED_CHATROOM_NOT_OPENED = 2
    DM_CHATROOM_NOT_OPENED = 3
    COMMUNITY_MODERATION_EMAIL = 4
    JOIN_FORM_EMAIL = 5


user_email_send_status_types = UserEmailSendStatusTypes()


class ChatroomNotOpenedTypes:
    TAGGED_CHATROOM = 1
    DM_CHATROOM = 2


chatroom_not_opened_types = ChatroomNotOpenedTypes()


class EventOnlineLinkTypes:
    ZOOM = 0
    MEET = 1
    OTHER = 2


event_online_link_types = EventOnlineLinkTypes()


class MessageTemplateChatroomTypes:
    DM_CHATROOM = 1


message_template_chatroom_types = MessageTemplateChatroomTypes()


class EditQuestionChangeStates:
    NEW_QUESTION = 0
    EDIT_QUESTION = 1
    DELETE_QUESTION = 2


question_change_states = EditQuestionChangeStates()


class EditFieldCommunityDataTypes:
    EDIT_NAME = "name"
    EDIT_PURPOSE = "purpose"
    EDIT_IMAGE_URL = "image_url"
    EDIT_DIRECTORY = "directory"


edit_field_community_data_types = EditFieldCommunityDataTypes()


class AirtableWebhookTypes:
    JOIN_COMMUNITY = "join_community"
    APPROVE_REQUEST = "approve_request"


airtable_webhook_types = AirtableWebhookTypes()


class WebhookTypes(enum.Enum):
    COMMUNITY_JOIN = 1


class CohortAccess(enum.Enum):
    NO_ACCESS = 0
    RESTRICTED_ACCESS = 1
    FULL_ACCESS = 2


class APIVersionHeaders:
    V1 = "v1"
    V2 = "v2"


api_version_headers = APIVersionHeaders()


class CommunityDMSettingsStateTypes:
    UNLIMITED = 0
    LIMITED = 1


community_dm_settings_state_types = CommunityDMSettingsStateTypes()


class CommunityDMSettingsDurationTypes:
    DAYS = "day"
    WEEKS = "week"
    MONTHS = "month"


community_dm_settings_duration_types = CommunityDMSettingsDurationTypes()


class BlockChatroomStates:
    BLOCK = 0
    UNBLOCK = 1


block_chatroom_states = BlockChatroomStates()


class DMChatRequestStates:
    INITIATED = 0
    ACCEPTED = 1
    REJECTED = 2


chat_request_states = DMChatRequestStates()


class DMIconFromStates:
    MEMBER_PROFILE = "member_profile"
    COMMUNITY_DETAIL = "community_detail"
    DM_FEED = "dm_feed"
    DM_FEED_V2 = "dm_feed_v2"
    MEMBER_DIRECTORY = "member_directory"
    CHATROOM = "chatroom"
    GROUP_CHANNEL = "group_channel"


dm_icon_from_states = DMIconFromStates()


class APITypes:
    Non_SDK = 0
    SDK = 1


api_types = APITypes()


class NotificationStates:
    ALL_MESSAGES = 1
    ONLY_MENTIONS_AND_REPLIES = 2
    DM_MENTION_REPLIES_POLL = 3

    ALL_MESSAGES_ANALYTICS = "all_messages"
    ONLY_MENTIONS_AND_REPLIES_ANALYTICS = "mentions_replies"
    DM_MENTION_REPLIES_POLL_ANALYTICS = "dm_mention_replies_poll"


noti_states = NotificationStates()


class FeedNotificationStates:
    LIKES = 1
    COMMENTS = 2
    REPLIES_ON_YOUR_COMMENTS = 3
    UPDATES_ON_COMMENTED_POST = 4


feed_notification_states = FeedNotificationStates()


class WhatsappSubscriptionStateActions:
    START = "START"
    STOP = "STOP"


whatsapp_subscription_state_actions = WhatsappSubscriptionStateActions()


class UnsubscribeTypes:
    MAIL_HAS_INSTALLED_APP = "mail_has_installed_app"
    MAIL_CARD_OWNER_INACTIVITY = "mail_card_owner_inactivity"
    MAIL_TAGGED_BUT_NOT_OPENED_CHATROOM = "mail_tagged_but_not_opened_chatroom"
    MAIL_SEND_CHATROOM_OWNER = "mail_send_chatroom_owner_mail"
    MAIL_EVENT_NOTIFICATIONS = "mail_event_notifications"
    MAIL_CHATROOM_OR_DM = "mail_chatroom_or_dm"


unsubscribe_types = UnsubscribeTypes()


class AccessTypes:
    CREATE_POST = "create_post"
    VIEW_POST = "view_post"
    DELETE_POST = "delete_post"
    PIN_POST = "pin_post"
    LIKE_POST = "like_post"
    SAVE_POST = "save_post"
    CREATE_COMMENT = "create_comment"
    VIEW_COMMENT = "view_comment"
    DELETE_COMMENT = "delete_comment"
    LIKE_COMMENT = "like_comment"
    CREATE_ACTIVITY = "create_activity"
    VIEW_ACTIVITY = "view_activity"
    VIEW_REPORT_ENTITY = "view_report_entity"
    EDIT_COMMENT = "edit_comment"
    EDIT_POST = "edit_post"
    CREATE_TOPIC = "create_topic"
    EDIT_TOPIC = "edit_topic"
    IS_MEMBER = "is_member"


access_types = AccessTypes()


class FeedOrderTypes:
    NEWEST_ORDER_TYPE = 0
    RECENTLY_ACTIVE_ORDER_TYPE = 1
    MOST_MESSAGES_ORDER_TYPE = 2
    MOST_PARTICIPANTS_ORDER_TYPE = 3


feed_order_types = FeedOrderTypes()


class ChatroomInviteStatusTypes:
    INVITE_INITIATED = 0
    INVITE_ACCEPTED = 1
    INVITE_REJECTED = 2


chatroom_invite_status_types = ChatroomInviteStatusTypes()


class ChatroomSettings:
    TAG_ONLY_PARTICIPANTS_ID = 29

    TAG_ONLY_PARTICIPANTS_TITLE = 'Tag only participants'


chatroom_setting_states = ChatroomSettings()


class DMFabShowList:
    ALL_MEMBERS = 1
    ONLY_CM = 2


class OTPTypes:
    MOBILE = "mobile"
    EMAIL = "email"
