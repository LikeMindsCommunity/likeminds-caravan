import time

from external_services.logging.logging_wrapper import LoggingWrapper
from togther.models import Card_Attachment, ModelUtilities, answerAttachment
from utility.json_utilities import JsonUtilities

info_logger = LoggingWrapper.get_instance()


def remove_decimal_valued_duration_from_meta_for_card_attachment():
    print("Updating for Card Attachment...")
    info_logger.info("Updating for Card Attachment...")
    card_attachment_list = ModelUtilities.get_model_filter(Card_Attachment, {})

    for card_attachment in card_attachment_list:

        if card_attachment.meta:
            meta_data = JsonUtilities.load_json_data(card_attachment.meta)

            if isinstance(meta_data, dict) and meta_data.get('duration'):

                if isinstance(meta_data.get('duration'), float):
                    print("Updating for PK: ", card_attachment.id)
                    info_logger.info("Updating for PK: {}".format(card_attachment.id))
                    meta_data['duration'] = int(meta_data.get('duration'))
                    json_dump = JsonUtilities.dump_json_data(meta_data)
                    card_attachment.meta = json_dump
                    card_attachment.save()


def remove_decimal_valued_duration_from_meta_for_answer_attachment():
    print("Updating for Answer Attachment...")
    info_logger.info("Updating for Answer Attachment...")

    answer_attachment_list = ModelUtilities.get_model_filter(answerAttachment, {})

    for answer_attachment in answer_attachment_list:

        if answer_attachment.meta:
            meta_data = JsonUtilities.load_json_data(answer_attachment.meta)

            if isinstance(meta_data, dict) and meta_data.get('duration'):

                if isinstance(meta_data.get('duration'), float):
                    print("Updating for PK: ", answer_attachment.id)
                    info_logger.info("Updating for PK: {}".format(answer_attachment.id))
                    meta_data['duration'] = int(meta_data.get('duration'))
                    json_dump = JsonUtilities.dump_json_data(meta_data)
                    answer_attachment.meta = json_dump
                    answer_attachment.save()


start_time = time.time()
remove_decimal_valued_duration_from_meta_for_card_attachment()
remove_decimal_valued_duration_from_meta_for_answer_attachment()
end_time = time.time()
time_taken = end_time - start_time

print(time_taken)
