from togther.models import collabcardState


def update_attending_status():
    state_list = [3, 4]
    collabcardState.objects.filter(state__in=state_list).update(attending_status=True)


update_attending_status()


