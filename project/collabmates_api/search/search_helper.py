
class SearchHelper:

    @staticmethod
    def has_attachments_uploaded(chatroom):
        if chatroom['attachment_count'] > 0 and chatroom['attachments_uploaded'] is False:
            return False

        return True
