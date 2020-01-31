

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
