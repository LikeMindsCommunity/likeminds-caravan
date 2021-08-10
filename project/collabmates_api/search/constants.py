CHATROOM_FIELD_HEADER = "header"
CHATROOM_FIELD_TITLE = "title"
CHATROOM_SEARCHABLE_FIELDS = [CHATROOM_FIELD_HEADER, CHATROOM_FIELD_TITLE]

MEMBER_DIRECTORY_FIELD_NAME = "name"
MEMBER_DIRECTORY_FIELD_TAG = "tag"
MEMBER_DIRECTORY_SEARCHABLE_FIELDS = [MEMBER_DIRECTORY_FIELD_NAME, MEMBER_DIRECTORY_FIELD_TAG]

MEMBER_DIRECTORY_INDEX_FIELDS_DICTIONARY_MAPPING = {
    MEMBER_DIRECTORY_FIELD_NAME: "member.user.name",
    MEMBER_DIRECTORY_FIELD_TAG: "custom_title"
}

CUSTOM_INTRO_TEXT_FOR_ADMIN = "Created this community on %s"
CUSTOM_INTRO_TEXT_FOR_MEMBERS = "Joined via a private community link on %s"
CUSTOM_CLICK_TEXT_FOR_MEMBERS = "%s joined this community via a private community link on %s and hasn’t created " \
                                 "their profile for this community yet"
