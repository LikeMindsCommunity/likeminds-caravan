from rest_framework.views import APIView
from django.http import JsonResponse
from rest_framework import serializers, fields
from togther.models import *
from collections import OrderedDict
import json
import time
from .serializers import get_answer_files, get_preview_for_url


def get_error_context(success, error_message):
    '''function to get error context for apis'''

    context = {
        'success': success,
        'error_message': error_message
    }
    return context


class reportsView(APIView):

    def get(self, request, *args, **kwargs):
        query_set = Report.objects.all().order_by("-id")[:2]
        serialized_obj = reportSerializer(query_set, many=True)
        return JsonResponse(serialized_obj.data, safe=False)


class communitySerializer(serializers.ModelSerializer):

    class Meta:
        model = Community
        fields = '__all__'


class chatroomSerializer(serializers.ModelSerializer):
    community = communitySerializer()

    class Meta:
        model = Collabcard
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(chatroomSerializer, self).__init__(*args, **kwargs)
        self.current_user_id = kwargs.get('current_user_id', None)


    def to_representation(self, obj):
        data = super(chatroomSerializer, self).to_representation(obj)

        fields = self._readable_fields

        for field in fields:
            if field.field_name == "community" and data['community'] is not None:
                data['community_id'] = data['community']["id"]
                data['community_name'] = data['community']["name"]
                if data['community']["image_link_round"]:
                    data['image_url_round'] = data['community']["image_link_round"]

                del data["community"]

            elif field.field_name == "has_been_named":
                pass
            elif data[field.field_name] is None:
                del data[field.field_name]



class membersSerializer(serializers.ModelSerializer):

    class Meta:
        model = Members
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(membersSerializer, self).__init__(*args, **kwargs)
        self.member_instance = kwargs.get('member_instance')
        self.community_id = kwargs.get('community_id')
        self.current_user_id = kwargs.get('current_user_id', None)
        self.send_profile = kwargs.get('send_profile', None)
        self.is_promoter = kwargs.get('is_promoter', None)
        self.is_owner = kwargs.get('is_owner', None)
        self.all_members_api = kwargs.get('all_members_api', None)
        self.profile_detail_api = kwargs.get('profile_detail_api', None)
        self.user_admin_rights = kwargs.get('user_admin_rights', None)
        self.parents_list = json.loads(self.member_instance.parent_cm_list) if self.member_instance.parent_cm_list else []

    def to_representation(self, obj):
        data = super(membersSerializer, self).to_representation(obj)

        fields = self._readable_fields

        for field in fields:
            if field.field_name == "community" and data['community'] is not None:
                data['community_id'] = data['community']["id"]
                data['community_name'] = data['community']["name"]
                del data["community"]
            elif data[field.field_name] is None:
                del data[field.field_name]

        # data = OrderedDict([(key, data[key]) for key in data if data[key] is not None])
        return data



    def get_menu_for_members(self, current_user_id, item_member_id, community_id, current_user_is_promoter, item_member_state,
                             current_user_is_owner=False, item_member_is_owner=False, current_user_admin_rights=None,
                             parents_list=None, profile_detail_api=False):
        """ function to get the menu for all members for all members api and profile detail api """
        #  x is current member , y is member whose profile is currently in iteration sequence
        # current_user_state, item_member_state,

        edit_title = {"title": "Edit title",
                      "route": f"route://edit_custom_title?community_id={community_id}&member_id={item_member_id}"}
        edit_permissions = {"title": "Edit permissions",
                            "route": f"route://edit_member_rights?community_id={community_id}&member_id={item_member_id}"}
        give_CM_rights = {"title": "Give community management rights",
                          "route": f"route://give_manager_rights?community_id={community_id}&member_id={item_member_id}"}
        edit_CM_rights = {"title": "Edit management rights",
                          "route": f"route://edit_manager_rights?community_id={community_id}&member_id={item_member_id}"}
        report_member = {"title": "Report member",
                         "route": f"route://report_member?community_id={community_id}&member_id={item_member_id}"}
        remove_from_community = {"title": "Remove from community",
                                 "route": f"route://remove_from_community?community_id={community_id}&member_id={item_member_id}"}
        block_member = {"title": "Block member",
                        "route": f"route://block_member?community_id={community_id}&member_id={item_member_id}"}

        if parents_list is None:
            parents_list = []

        if current_user_is_owner and int(current_user_id) == int(item_member_id):
            return [edit_title]
        if current_user_id and int(current_user_id) == int(item_member_id):
            return []
        elif not current_user_id:
            return []

        menu = []

        if current_user_is_owner and item_member_is_owner:
            menu = [edit_title]
        elif current_user_is_owner and item_member_state == member_states.ADMIN:
            menu = [remove_from_community, edit_CM_rights]

        elif current_user_is_owner and item_member_state == member_states.MEMBER:
            menu = [remove_from_community, edit_permissions, give_CM_rights]

        elif current_user_is_promoter and item_member_state == member_states.ADMIN:

            is_child = current_user_id in parents_list

            if current_user_admin_rights:
                if current_user_admin_rights["approve"] and is_child:
                    menu.append(remove_from_community)

                if current_user_admin_rights["add_manager"] and is_child:
                    menu.append(edit_CM_rights)

            if profile_detail_api:
                menu.append(report_member)
                # if not item_member_is_owner:
                menu.append(block_member)

        elif current_user_is_promoter and item_member_state == member_states.MEMBER:
            if current_user_admin_rights:
                if current_user_admin_rights["approve"]:
                    menu.append(remove_from_community)

                if current_user_admin_rights["delete_room"] or current_user_admin_rights["approve"]:
                    menu.append(edit_permissions)

                if current_user_admin_rights["add_manager"]:
                    menu.append(give_CM_rights)

                if not current_user_admin_rights["approve"] and profile_detail_api:
                    menu.append(report_member)

                if profile_detail_api:
                    menu.append(block_member)

        else:
            if profile_detail_api:
                menu.append(report_member)
                # if not item_member_is_owner:
                menu.append(block_member)

        return menu


class formSerializer(serializers.ModelSerializer):

    class Meta:
        model = Members
        fields = '__all__'


class reportSerializer(serializers.ModelSerializer):
    # community = communitySerializer()
    # collabcard = chatroomSerializer()

    class Meta:
        model = Report
        fields = '__all__'
        depth = 1

    def to_representation(self, obj):
        data = super(reportSerializer, self).to_representation(obj)

        fields = self._readable_fields

        for field in fields:
            if field.field_name == "community" and data['community'] is not None:
                data['community_id'] = data['community']["id"]
                data['community_name'] = data['community']["name"]
                del data["community"]
            elif data[field.field_name] is None:
                del data[field.field_name]

        # data = OrderedDict([(key, data[key]) for key in data if data[key] is not None])
        return data


class memberCommunityProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = Members
        fields = '__all__'
        depth = 1

    def __init__(self, *args, **kwargs):
        super(memberCommunityProfileSerializer, self).__init__(*args, **kwargs)
        self.member_ids = kwargs.get('member_ids')
        self.community_id = kwargs.get('community_id')
        self.current_user_id = kwargs.get('current_user_id', None)
        self.send_profile = kwargs.get('send_profile', None)
        self.remove = kwargs.get('remove', None)
        self.is_promoter = kwargs.get('is_promoter', None)
        self.is_owner = kwargs.get('is_owner', None)
        self.all_members_api = kwargs.get('all_members_api', None)
        self.profile_detail_api = kwargs.get('profile_detail_api', None)
        self.user_admin_rights = kwargs.get('user_admin_rights', None)


def get_members_profile(member_ids, community_id, current_user_id=None, send_profile=True, remove=False,
                        is_promoter=False, is_owner=False, all_members_api=False, profile_detail_api=False,
                        user_admin_rights=None):

    '''function to get member profile from list of members ids'''
    member_profile_list = []

    for id in member_ids:

        member_filter = Members.objects.filter(member_id=id, community_id=community_id)

        if member_filter.exists():

            if user_admin_rights and not user_admin_rights["approve"]:
                if member_filter[0].state == member_states.PENDING_MEMBER:
                    continue

            community_profile = MembersSerializer(member_filter[0], community_id, current_user_id=current_user_id,
                                                  send_profile=send_profile, all_members_api=all_members_api,
                                                  profile_detail_api=profile_detail_api, user_admin_rights=user_admin_rights,
                                                  is_owner=is_owner, is_promoter=is_promoter
                                                  )
            member_profile_list.append(community_profile)

        else:
            temp = get_user_profile(id, community_id, current_user_id=current_user_id,send_profile=send_profile,remove=remove)
            temp['state'] = 0
            member_profile_list.append(temp)

    return member_profile_list


class CardAnswersDBSyncSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    images = serializers.ListField(write_only=True)
    pdf = serializers.ListField(write_only=True)
    location = serializers.ListField(write_only=True)
    reply_conversation = serializers.DictField(write_only=True)
    preview = serializers.DictField(write_only=True)
    member_id = serializers.CharField(write_only=True)

    class Meta:
        model = card_answers
        fields = ("id", 'answer', 'card', 'user', 'created_at', 'community', 'state',
                  'og_tags', 'is_deleted', 'deleted_by_user', 'deleted_by_user_state',
                  'is_edited', 'reply', 'internal_link', 'has_files', 'date', 'images',
                  'pdf', 'location', 'reply_conversation', 'preview', 'member_id')

    def __init__(self, *args, **kwargs):
        super(CardAnswersDBSyncSerializer, self).__init__(*args, **kwargs)
        self.fetch_reply = self.context.get('fetch_reply', True)
        self.current_user_id = self.context.get('current_user_id', None)

    def get_date(self, obj):
        return time.strftime('%d %b %Y', time.localtime(obj.created_at))

    def to_representation(self, obj):
        data = super(CardAnswersDBSyncSerializer, self).to_representation(obj)

        fields = self._readable_fields

        for field in fields:

            if field.field_name == "community" and data['community'] is not None:
                data['community_id'] = data['community']
                del data["community"]

            elif field.field_name == "card" and data['card'] is not None:
                data['chatroom_id'] = data['card']
                del data["card"]

            elif field.field_name == "user" and data['user'] is not None:
                data['member_id'] = data['user']
                del data["user"]

            elif field.field_name == "created_at" and data['created_at'] is not None:
                data['created_at'] = time.strftime('%H:%M', time.localtime(data['created_at']))

            elif field.field_name == "og_tags":
                if data['og_tags'] is not None:
                    data['og_tags'] = json.loads(data['og_tags'])
                else:
                    del data['og_tags']

            elif field.field_name == "has_files" and data['has_files']:
                answer_files = get_answer_files(data['id'])
                data['images'] = answer_files['image']
                data['pdf'] = answer_files['pdf']
                if 'location' in answer_files:
                    data['location'] = answer_files['location']

            elif field.field_name == "deleted_by_user":
                if not data['is_deleted']:
                    del data['deleted_by_user']

            elif field.field_name == "deleted_by_user_state":
                if not data['is_deleted']:
                    del data['deleted_by_user_state']

            elif field.field_name == "reply" and data['reply'] is not None and self.fetch_reply:
                data['reply_conversation'] = CardAnswersDBSyncSerializer(fetch_reply=False,
                                                                         current_user_id=self.current_user_id)
            elif field.field_name == "internal_link" and data['internal_link'] is not None:
                data['preview'] = get_preview_for_url(member_id=self.current_user_id,
                                                      preview_url=data['internal_link'])
                del data['internal_link']

            elif data[field.field_name] is None:
                del data[field.field_name]

        return data


