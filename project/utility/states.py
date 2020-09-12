import enum


# member state
class ChatroomActions:

    ACTION_RENAME = 1
    ACTION_VIEW_PARTICIPANTS = 2
    ACTION_INVITE = 3
    ACTION_FOLLOW = 4
    ACTION_VIEW_COMMUNITY = 5
    ACTION_MUTE = 6
    ACTION_DELETE = 7
    ACTION_UNMUTE = 8
    ACTION_UNFOLLOW = 9
    ACTION_REPORT = 10


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


class ChatroomStates:
    ANSWER = 0
    CHATROOM_HEADER = 1
    CHATROOM_FOLLOW = 2
    CHATROOM_UNFOLLOW = 3
    CHATROOM_CREATER = 4
    CHATROOM_COMMUNITY_EDIT = 5

    CHATROOM_GUEST = 6

chatroom_states = ChatroomStates()

class MultipleSelectPoll:
    #class to save states of multiple select poll
    EXACTLY = 0
    AT_MAX = 1
    AT_MOST = 1
    AT_LEAST = 2

multiple_select_poll = MultipleSelectPoll()

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

deleted_members = DeletedMembers()

# community types
class CommunityTypes(enum.IntEnum):
    TYPE_NONE = -1
    TYPE_LC_GC = 0
    TYPE_LH_GC = 1
    TYPE_LC_PS = 2
    TYPE_LC_PI = 3
    TYPE_IH_GC = 4
    TYPE_IS_GC = 5
    TYPE_IF_GC = 6
    TYPE_IC_GC = 7
    # TYPE_PI_GC = 8
    # TYPE_PS_GC = 9
    # TYPE_GN = 10
    # TYPE_SS_GN = 11
    # TYPE_SS_GC = 12

# community attributes
class CommunityAttributes(enum.IntEnum):
    Legacy_work = 1
    Legacy_education = 2
    Legacy_hometown = 3
    Legacy_lifestyle = 4
    Profession_skill = 5
    Profession_industry = 6
    Profession_designation = 7
    Interests_cause = 8
    Interests_hobby = 9
    Interests_sports = 10
    Interests_fan = 11
    Geography_city = 12
    Geography_state = 13
    Geography_country = 14
    Geography_pincode = 15
    Global = 16
    Legacy_uncategorized = 17
    Profession_uncategorized = 18
    Interests_uncategorized = 19
    Geography_uncategorized = 20


class QuestionStates:
    TEXT = 0
    CHOICE_SINGLE = 1
    CHOICE_MULTIPLE = 2
    TEXT_WITH_LIMIT = 3
    PARAGRAPH = 4
    FILE_UPLOAD = 5
    DATE_TIME = 6
    INTRODUCTION = 7
    PROFILE_LINK=8
    MOBILE_NO = 9
    EMAIL_ID = 10

    GOOGLE_CITY_FETCH = 11

question_states=QuestionStates()



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