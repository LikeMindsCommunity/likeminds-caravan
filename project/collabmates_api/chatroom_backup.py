import time
from togther.models import (deletedChatrooms, Report_Tags, collabcardState, CollabcardStateBackup)

def create_chatroom_delete_backup(card_instance, current_user_instance, tag_id, reason, card_creator=False,
                                        promoter=False):
    deleted_filter = deletedChatrooms.objects.filter(card_id=card_instance.id)

    if deleted_filter.exists():
        return
    card = deletedChatrooms()
    card.title = card_instance.title
    card.community = card_instance.community
    card.user = card_instance.user
    card.type = card_instance.type
    card.image_count = card_instance.image_count
    card.pdf_count = card_instance.pdf_count
    card.date_time = card_instance.date_time
    card.duration = card_instance.duration

    # for event card
    card.location = card_instance.location
    card.location_lat = card_instance.location_lat
    card.location_long = card_instance.location_long
    card.start_date = card_instance.start_date
    card.end_date = card_instance.end_date
    card.about = card_instance.about
    card.co_hosts = card_instance.co_hosts
    card.online_link = card_instance.online_link

    # for poll card
    card.multiple_select = card_instance.multiple_select
    card.multiple_select_no = card_instance.multiple_select_no
    card.multiple_select_state = card_instance.multiple_select_state
    card.poll_type = card_instance.poll_type
    card.is_poll_anonymous = card_instance.is_poll_anonymous
    card.allow_add_option = card_instance.allow_add_option

    # for chatroom header
    card.header = card_instance.header

    card.share_link = card_instance.share_link
    card.og_tags = card_instance.og_tags

    card.deleted_by_user = current_user_instance
    text = "creator"
    if promoter:
        text = "community manager"
    card.deleted_by_text = text
    card.deleted_by_creator = card_creator
    card.deleted_by_promoter = promoter
    if reason:
        card.reason = reason
    if tag_id:
        tag = Report_Tags.objects.filter(tag_id=tag_id)
        if tag.exists():
            card.tag = tag[0]

    card.date_epoch = time.time()  # card creation time
    card.card_id = card_instance.id
    card.save()

    create_chatroom_participants_backup(card_instance=card_instance, deleted_card_instance=card)


def create_chatroom_participants_backup(card_instance, deleted_card_instance):
    participants_list = collabcardState.objects.filter(card=card_instance).filter(follow_status=True).distinct("user")
    for participant in participants_list:
        create_collbacard_state_backup(participant, deleted_card_instance=deleted_card_instance)

def create_collbacard_state_backup(collabcard_state_instance, deleted_card_instance):

    backup_instance = CollabcardStateBackup()
    backup_instance.card = deleted_card_instance
    backup_instance.community = collabcard_state_instance.community
    backup_instance.user = collabcard_state_instance.user
    backup_instance.state = collabcard_state_instance.state
    backup_instance.remove = collabcard_state_instance.remove
    backup_instance.seen_status = False
    backup_instance.mute_status = collabcard_state_instance.mute_status
    backup_instance.follow_status = collabcard_state_instance.follow_status
    backup_instance.is_guest = collabcard_state_instance.is_guest
    backup_instance.source = collabcard_state_instance.source
    backup_instance.save()