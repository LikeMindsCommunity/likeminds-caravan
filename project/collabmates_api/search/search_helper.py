from togther.models import (ModelUtilities, Collabcard)


class SearchHelper:

    @staticmethod
    def has_attachments_uploaded(chatroom):
        if chatroom['attachment_count'] > 0 and chatroom['attachments_uploaded'] is False:
            return False

        return True

    @staticmethod
    def update_chatroom_member_to_creator_for_card_data(chatroom_data):

        chatroom_ids_list = [state_data.get('chatroom').get('id') for state_data in chatroom_data
                             if state_data.get('chatroom')]

        card_creators_data = ModelUtilities.get_model_filter(
            Collabcard, {'id__in': chatroom_ids_list}).select_related('user').values('id', 'user__id',
                                                                                     'user__userinfo__name')

        card_creators_data = {creator_data.get('id'): creator_data for creator_data in card_creators_data}

        for card_data in chatroom_data:
            creator_data = card_creators_data.get(card_data.get('chatroom').get('id'))

            card_data['member'] = {
                'id': creator_data.get('user__id'),
                'profile': {
                    'name': creator_data.get('user__userinfo__name')
                }
            }

        return chatroom_data
