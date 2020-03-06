import enum

# collabcard types
class CollabcardTypes:
    CARD_NORMAL = 0
    CARD_INTRO = 1
    CARD_EVENT = 2
    CARD_POLL = 3

card_types = CollabcardTypes()
# collabcard states
class CollabcardStates:
    COLLABCARD_STATE_SEEN = 1
    COLLABCARD_STATE_FOLLOW = 2

    COLLABCARD_STATE_UNATTEND_FOLLOWING = COLLABCARD_STATE_FOLLOW
    COLLABCARD_STATE_ATTEND_FOLLOWING = 3
    COLLABCARD_STATE_ATTEND_UNFOLLOWING = 4

collabcard_states = CollabcardStates()


# member state
class MemberStates:
    ADMIN = 1
    TEMP_ADMIN = 2
    PENDING_MEMBER = 3
    MEMBER = 4
    DECLINED_MEMBER = 5
    UNKNOWN_NOMINATED_PROMOTER = 6
    KNOWN_NOMINATED_PROMOTER = 7
    INTERESTED_MEMBER = 8
    ELIGIBLE_MEMBER = 9

member_states = MemberStates()


# community types
class CommunityTypes(enum.IntEnum):
    TYPE_NONE = -1
    TYPE_LC_GC = 0
    TYPE_LH_GC = 1
    TYPE_LC_PS = 2
    TYPE_IH_GC = 3
    TYPE_IS_GC = 4
    TYPE_IF_GC = 5
    TYPE_IC_GC = 6
    TYPE_PI_GC = 7
    TYPE_PS_GC = 8
    TYPE_GN = 9
    TYPE_SS_GN = 10
    TYPE_SS_GC = 11

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
    PARAGRAPH = 4
    FILE_UPLOAD = 5
    DATE_TIME = 6
    INTRODUCTION = 7

question_states=QuestionStates()