import time

from django.contrib.auth.models import User

from collabmates_api.sync.model_update import update_models_for_syncing_apis
from collabmates_api.upload_attachments import get_user_image_based_on_community, save_chatroom_attachments
from collabmates_api.utility import pagination
from collabmates_api.views import post_master_introductions_for_community, \
    create_conversation_context_for_intro_chatrooms, post_member_directory_link

from togther.models import Members, Collabcard, collabcardState, Community, ModelUtilities, card_answers, \
    Card_Attachment

from utility.states import SyncTypes
from utility.time_utilities import TimeUtilities
from external_services.logging.logging_wrapper import LoggingWrapper

info_logger = LoggingWrapper.get_instance()


def perform_soft_delete_for_dublicate_intro_rooms():
    community_list = [49792, 49825, 49813, 49751, 49722, 49788, 49694]

    for community_id in community_list:
        master_intro = ModelUtilities.get_model_filter(Collabcard, {'type': 9, 'community': community_id})

        if master_intro:
            instance = master_intro[0]
            instance.is_deleted = True
            instance.deleted_by = instance.user
            instance.save()
            current_time = TimeUtilities.current_time_in_sec()
            ModelUtilities.model_update(collabcardState, {'card': instance}, {'updated_at': current_time})
            log = "Instance deleted -- %s" % (str(instance.card.id))

            print(log)


def post_introductions_card_for_communities(community_list):
    for community in community_list:

        master_community_list = []
        member_filter = ModelUtilities.get_model_filter(Members,
                                                        {'state': 1, 'is_owner': True, 'community_id': community})

        if member_filter:
            member_instance = member_filter[0]
            user_instance = member_instance.member_id
            community_instance = member_instance.community_id

            community_id = community_instance.id
            member_id = user_instance.id

            print(community_id)
            print(member_id)

            context = post_master_introductions_for_community(user_instance.id, community_instance.id)

            if context:
                print(context['collabcard']['id'])
                info_logger.info(context['collabcard']['id'])

            update_models_for_syncing_apis(SyncTypes.COMMUNITY,
                                           {'community_id': community_id},
                                           {'order_time': TimeUtilities.current_time_in_milliseconds()})

            post_member_directory_link(user_instance, community_instance)
            master_community_list.append(community_id)
            print("\n")
            time.sleep(3)

        print(master_community_list)


def save_individual_intro_card_in_cache(community_list):
    for community in community_list:
        card_filter = Collabcard.objects.filter(type=1, community=community).order_by('id')

        for card_instance in card_filter:
            master_intro = Collabcard.objects.filter(type=9,
                                                     community=card_instance.community)

            if master_intro:
                master_intro_instance = master_intro[0]
                image_url = get_user_image_based_on_community(card_instance.user.id, card_instance.community.id)

                if image_url:

                    if not ModelUtilities.is_model_filter_exists(Card_Attachment, {'image_url': image_url,
                                                                                   'collabcard': card_instance}):
                        save_chatroom_attachments(card_instance, body={
                            'url': image_url,
                            'type': "image",
                            'index': 1
                        })
                        ModelUtilities.model_update(Collabcard, {'id': card_instance.id},
                                                    {'has_files': True, 'attachment_count': 1,
                                                     'attachments_uploaded': True})

                answer_instance = create_conversation_context_for_intro_chatrooms(card_instance, card_instance.user,
                                                                                  master_intro_instance)
                print(answer_instance)
                info_logger.info(answer_instance)

                current_time = TimeUtilities.current_time_in_sec()
                ModelUtilities.model_update(collabcardState, {'card': card_instance}, {'updated_at': current_time})
                print("\n")
                time.sleep(1)


def saving_updated_at_for_intro_rooms_for_syncing():
    card_filter = ModelUtilities.get_model_filter(Collabcard, {'type': 1})

    for card_instance in card_filter:
        current_time = TimeUtilities.current_time_in_sec()
        ModelUtilities.model_update(collabcardState, {'card': card_instance}, {'updated_at': current_time})
        time.sleep(0.5)
        log = "updated time -- %s" % (str(card_instance.id))

        print(log)


def create_introduction_card_conversations():
    # community_list = [49792, 49825, 49813, 49751, 49722, 49788, 49694]
    community_list = [49751]  # LMCM community
    start_time = TimeUtilities.current_time_in_sec()
    post_introductions_card_for_communities(community_list)
    #save_individual_intro_card_in_cache(community_list)
    end_time = TimeUtilities.current_time_in_sec()

    print(end_time - start_time)


create_introduction_card_conversations()
