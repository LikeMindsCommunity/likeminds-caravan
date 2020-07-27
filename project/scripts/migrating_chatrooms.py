from togther.models import collabcardState,conversationEngage,Collabcard




def update_followed_members():

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


    print("existing chatroom followed for users")





def set_name_of_chatrooms():

    collabcard_filter = Collabcard.objects.all().order_by('id')

    for instance in collabcard_filter:
        header = None
        if not instance.header:
            if instance.type == 7:
                header= """Resources: %s"""%(instance.community.name)
            elif instance.type == 1:
                header=  """%s's Intro"""%(str(instance.user.userinfo.name))
            else:
                if len(instance.title) <= 30:
                    header= instance.title[:30]
                else:
                    header= instance.title[:27] + "..."

            instance.header = header
            instance.has_been_named = True

            instance.save()

            print("card id ", str(instance.id))

    print("name set in chatrooms")



update_followed_members()
set_name_of_chatrooms()