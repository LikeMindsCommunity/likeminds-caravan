import time
from togther.models import ModelUtilities, userEmails

def lowercase_emails():
    '''
    Function to convert emails to lowercase
    '''

    start = time.time()

    users_to_update = []
    model_utilities = ModelUtilities()
    
    # Fetch all users whose email contains uppercase letters
    for user_email in model_utilities.get_model_filter(userEmails, {}):

        if not user_email.email:
            continue

        if user_email.email != user_email.email.lower():
            user_email.email = user_email.email.lower()
            users_to_update.append(user_email)
    
    # Bulk update to minimize database hits
    if users_to_update:
        userEmails.objects.bulk_update(users_to_update, ['email'])
        print(f"Updated {len(users_to_update)} email(s) to lowercase.")
    else:
        print("No emails needed updating.")

    print(f"Completed in {time.time()-start} seconds.")

    return

lowercase_emails()

