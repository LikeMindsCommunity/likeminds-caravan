import time
import uuid
from togther.models import ModelUtilities, Userinfo


def fill_user_unique_id():
    all_users = ModelUtilities.get_model_filter(Userinfo, {})

    for user in all_users:

        if user.user_unique_id:
            continue

        user.user_unique_id = str(uuid.uuid4())
        user.save()


start = time.time()
fill_user_unique_id()
print("Completed in", time.time() - start)
