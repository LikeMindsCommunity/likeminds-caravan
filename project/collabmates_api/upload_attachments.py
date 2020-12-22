from utility.firebase import upload_community_thumbnail
from togther.models import (Collabcard, Community,
                            createCommunityAction, communityUpdate, Card_Attachment,
                            draftPolls, draftChatroom, draftChatroomFiles,
                            CollabcardPolls, answerAttachment)
from django.contrib.auth.models import User
import json
import ast
import time


def save_community_image(body, member_id):

    community_id = body['community_id']

    try:
        community = Community.objects.get(id=community_id)

    except Community.DoesNotExist:
        return {'success': False, 'error_message': "community does not exist"}

    if 'url' not in body:
        return {'success': False, 'error_message': "send uploaded file url"}

    community.image_link = body['url']
    community.image_link_round = body['url']
    community.save()

    upload_community_thumbnail.delay(community_id, body['url'])

    # updating the create community second step
    createCommunityAction.objects.filter(community=community,
                                         step_no="Step 2").update(current_point=10)

    # saving the update image details if the image is updated
    edit = body.get('edit', False)
    if edit == 'true':
        if not member_id:
            return {'success': False, 'error_message': "Send member id in headers"}
        else:
            try:
                member_instance = User.objects.get(id=member_id)
            except User.DoesNotExist:
                return {'success': False, 'error_message': "Member does not exist"}

        update_community(member_instance, community)

    return None


def update_community(member_instance, community):
    instance = communityUpdate()
    instance.updated_field = "image"
    instance.updated_time = time.time()
    instance.updated_member = member_instance
    instance.community = community
    instance.save()


def save_chatroom_attachments(chatroom_instance, body):
    file = Card_Attachment()
    file.collabcard = chatroom_instance
    file.type = body.get('type', None)
    file.file_url = body.get('url', None)
    file.index = body.get('index', 1)
    file.width = body.get('width', None)
    file.height = body.get('height', None)
    file.dimensions = get_image_dimensions(body.get('dimensions', None))
    file.save()


def save_conversation_attachments(body, conversation_instance):

    file = answerAttachment()
    file.answer = conversation_instance
    file.type = body.get('type', None)
    file.file_url = body.get('url', None)
    file.index = body.get('index', None)
    file.location_name = body.get('location_name', None)
    file.location_lat = body.get('location_lat', None)
    file.location_long = body.get('location_long', None)
    file.width = body.get('width', None)
    file.height = body.get('height', None)
    file.dimensions = get_image_dimensions(body.get('dimensions', None))
    file.save()


def save_poll_attachments(body):
    instance = CollabcardPolls.objects.get(id=body['poll_id'])
    instance.image_url = body.get('url', None)
    instance.save()


def save_draft_attachments(body):

    draft_id = body['draft_id']
    draft_instance = draftChatroom.objects.get(id=draft_id)

    instance = draftChatroomFiles()
    instance.draft = draft_instance
    instance.type = body.get('type', None)
    instance.file_url = body.get('url', None)
    instance.index = body.get('index', 1)
    instance.width = body.get('width', None)
    instance.height = body.get('height', None)
    instance.dimensions = get_image_dimensions(body.get('dimensions', None))
    instance.save()


def save_draft_poll_attachments(body):
    instance = draftPolls.objects.get(id=body['draft_poll_id'])
    instance.image_url = body.get('url', None)
    instance.save()


def get_image_dimensions(img_dimensions):

    if img_dimensions is None:
        return None

    if isinstance(img_dimensions, str):
        try:
            img_dimensions = json.loads(img_dimensions)
        except:
            img_dimensions = ast.literal_eval(img_dimensions)

        img_dimensions = json.dumps(img_dimensions)
    return img_dimensions

