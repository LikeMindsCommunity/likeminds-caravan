from togther.models import Community, Collabcard, card_answers
from .constants import BRANCH_DECODE_URI
from collabmates_api.static_text import BRANCH_LINK_PREFIX_ANDROID, BRANCH_LINK_PREFIX_IOS
import requests
from collabmates_api.serializers import get_preview_for_url
from django.conf import settings
from .celery_tasks import update_preview_of_chatroom_in_cache, update_preview_of_community_in_cache


class PreviewUtilities:

    def get_preview_url(self, preview_url):
        """ get internal link from branch link """

        if settings.URL in preview_url or \
                settings.WEB_URL in preview_url:
            return preview_url

        elif BRANCH_LINK_PREFIX_ANDROID in preview_url or \
                BRANCH_LINK_PREFIX_IOS in preview_url:

            preview_url = "https://" + preview_url.split('//')[1]
            return preview_url

        elif preview_url is None or not preview_url:
            return None

        else:
            # API request
            api_endpoint = BRANCH_DECODE_URI % (preview_url, settings.BRANCH_KEY)
            headers = {'Accept': 'application/json'}
            r = requests.get(url=api_endpoint, headers=headers)

            if r.status_code == 200:
                try:
                    data = r.json()
                    deep_link = data["data"]['$deep_link']
                    return deep_link

                except Exception as e:
                    return None

            return None

    def set_preview_object(self, instance, res, user_id):

        if 'internal_link' in res and res['internal_link']:
            self.set_preview_with_internal_link(instance, res, user_id)
            self.set_previw_object_in_cache(res, instance)

        if 'preview' in res and res['preview']:
            self.set_preview_with_preview_dict(instance, res, user_id)
            self.set_previw_object_in_cache(res, instance)

    def set_preview_with_internal_link(self, instance, res, user_id):
        try:
            internal_link = self.get_preview_url(res['internal_link'])
            instance.internal_link = internal_link

            if 'preview' not in res and internal_link is not None:
                preview = get_preview_for_url(user_id, internal_link)

                if preview:
                    res['preview'] = preview

        except Exception as e:
            self.remove_preview_instance(instance)

    def set_preview_with_preview_dict(self, instance, res, user_id):
        try:
            preview = res['preview']
            instance.preview_type = preview['preview_type']
            preview_community = Community.objects.get(pk=preview['community']["id"])
            instance.preview_community = preview_community

            if 'chatroom' in preview:
                preview_chatroom = Collabcard.objects.get(pk=preview['chatroom']["id"])
                instance.preview_chatroom = preview_chatroom

            if 'internal_link' not in res:
                if 'internal_link' in preview and preview['internal_link']:
                    instance.internal_link = self.get_preview_url(preview['internal_link'])
        except:
            self.remove_preview_instance(instance)

    def remove_preview_instance(self, instance):
        instance.internal_link = None
        instance.preview_community = None
        instance.preview_chatroom = None

    def set_previw_object_in_cache(self, res, instance):

        preview_obj = res.get('preview')

        if preview_obj and isinstance(instance, card_answers) and preview_obj.get('preview_type') == "chatroom":
            update_preview_of_chatroom_in_cache.delay({'chatroom_id': preview_obj['chatroom']["id"],
                                                       'preview_object': preview_obj,
                                                       'conversation_id': instance.id})

        if preview_obj and \
                isinstance(instance, card_answers) and \
                (preview_obj.get('preview_type') == "community" or preview_obj.get('preview_type') == "directory"):
            update_preview_of_community_in_cache.delay({'community_id': preview_obj['community']["id"],
                                                       'preview_object': preview_obj,
                                                        'conversation_id': instance.id})
