from utility.firebase import upload_community_thumbnail
from togther.models import (Collabcard, Community,
                            createCommunityAction, communityUpdate, Card_Attachment,
                            draftPolls, draftChatroom, draftChatroomFiles,
                            CollabcardPolls, answerAttachment)
from django.contrib.auth.models import User
import json
import ast
import time

g
def save_community_image(request, body, member_id):
    community_id = body['community_id']
    community = Community.objects.get(id=community_id)
    community.image_link = body['url']
    community.image_link_round = body['url']
    upload_community_thumbnail.delay(community_id, body['url'])
    community.save()
    # updating the create community second step
    createCommunityAction.objects.filter(community=community, step_no="Step 2").update(
        current_point=10)

    # saving the update image details if the image is updated
    edit = request.GET.get('edit', False)
    if edit == 'true':
        if not member_id:
            return {'success': False, 'error_message': "Send member id in headers"}
        else:
            member_instance = User.objects.get(id=member_id)

        instance = communityUpdate()
        instance.updated_field = "image"
        instance.updated_time = time.time()
        instance.updated_member = member_instance
        instance.community = community
        instance.save()
    return None


def save_chatroom_attachments(card_instance, body):
    file = Card_Attachment()
    file.collabcard = card_instance
    file.type = body['type']
    file.file_url = body['url']
    file.index = body['index'] if 'index' in body else 1
    file.dimensions = get_image_dimensions(body.get('dimensions', None))
    file.save()


def save_conversation_attachments(body, answer_instance):

    file = answerAttachment()
    file.answer = answer_instance
    file.type =  body['type']
    file.file_url = body['url'] if 'url' in body else None
    file.index = body['index'] if 'index' in body else 1
    file.location_name = body['location_name'] if 'location_name' in body else None
    file.location_lat = body['location_lat'] if 'location_lat' in body else None
    file.location_long = body['location_long'] if 'location_long' in body else None
    file.dimensions = get_image_dimensions(body.get('dimensions', None))
    file.save()


def save_poll_attachments(body):
    instance = CollabcardPolls.objects.get(id=body['poll_id'])
    instance.image_url = body['url']
    instance.save()


def save_draft_attachments(body):

    attachment_type = body['type']
    draft_id = body['draft_id']
    draft_instance = draftChatroom.objects.get(id=draft_id)

    instance = draftChatroomFiles()
    instance.draft = draft_instance
    instance.file_url = body['url']
    instance.index = body['index'] if 'index' in body else 1
    instance.type = attachment_type
    instance.dimensions = get_image_dimensions(body.get('dimensions', None))
    instance.save()


def save_draft_poll_attachments(body):
    instance = draftPolls.objects.get(id=body['draft_poll_id'])
    instance.image_url = body['url']
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

