from togther.models import collabcardState,conversationEngage


def get_followed_members():

    followed_filter = collabcardState.objects.filter(follow_status=True).order_by('id')


    for instance in followed_filter:

        engage_filter = conversationEngage.objects.filter(card=instance.card,user=instance.user)

        if not engage_filter.exists():

            engage_instance = conversationEngage()

            engage_instance.card = instance.card
            engage_instance.user = instance.user
            engage_instance.created_at = instance.created_at
            engage_instance.updated_at = instance.updated_at

            engage_instance.save()


            print("card id",str(instance.card.id))





get_followed_members()