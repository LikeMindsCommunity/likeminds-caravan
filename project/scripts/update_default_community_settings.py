from togther.models import CommunitySettings, ModelUtilities

def update_settings():
    settings_to_update = ['feed', 'chatrooms', 'post_groups', 'direct_messages']

    ModelUtilities.get_model_filter(CommunitySettings, {'setting_type__in': settings_to_update}).update(enabled = True)

    print("feed, chatrooms, post_groups, direct_messages settings enabled for all communitites.")
