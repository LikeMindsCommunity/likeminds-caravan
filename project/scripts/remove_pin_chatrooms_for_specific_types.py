import time

from togther.models import (ModelUtilities, Collabcard)
from utility.states import (card_types, SyncTypes)
from collabmates_api.sync.model_update import (update_models_for_syncing_apis)


def remove_pin_chatrooms():
    card_filter = ModelUtilities.get_model_filter(Collabcard, {'is_pinned': True}).exclude(
        type__in=[card_types.CARD_NORMAL, card_types.CARD_POLL, card_types.CARD_PURPOSE])

    card_ids_list = list(card_filter.values_list('id', flat=True))

    card_filter.update(is_pinned=False)

    filter_dict = {
        'card_id__in': card_ids_list
    }

    updated_count = update_models_for_syncing_apis(SyncTypes.CHATROOM, filter_dict=filter_dict, update_dict={})
    print("Chatrooms update count -->", len(card_ids_list))
    return


start = time.time()
print("Starting script")
remove_pin_chatrooms()
print("Completed in -->", time.time() - start)
