import datetime

from external_services.caching.cache_impl import CacheImpl
from togther.models import ModelUtilities, Community, Members, CommunityUserDelete, Collabcard, collabcardState, \
    card_answers
from django.contrib.auth.models import User
from django.db.models import F

from utility.time_utilities import TimeUtilities


def delete_community(community_id: int, user_id: int) -> None:
    if not community_id or not user_id:
        print(f'missing community id or user id param')

    check_dependency: bool = check_community_delete_dependencies(community_id, user_id)
    if not check_dependency:
        return

    add_community_members_to_community_user_delete(community_id)
    delete_community_preview_cache(community_id)
    delete_chatroom_previews(community_id)
    delete_conversation_previews(community_id)
    delete_community_instance(community_id)

    print(f'community deletion successful at {datetime.datetime.now()}...')


def check_community_delete_dependencies(community_id: int, user_id: int) -> bool:
    check_community: bool = check_community_exist(community_id)
    if not check_community:
        return False

    check_user: bool = check_user_exist(user_id)
    if not check_user:
        return False

    check_permission: bool = check_community_delete_permission_for_user(community_id, user_id)
    if not check_permission:
        return False

    return True


def check_user_exist(user_id: int) -> bool:
    user: User = ModelUtilities.get_model_instance_or_none(User, user_id)
    if not user:
        message: str = f'user does not exist, id: {user_id}'
        print(message)
        return False

    return True


def check_community_exist(community_id: int) -> bool:
    community: Community = ModelUtilities.get_model_instance_or_none(Community, community_id)
    if not community:
        message: str = f'community does not exist, id: {community_id}'
        print(message)
        return False

    return True


def check_community_delete_permission_for_user(community_id: int, user_id: int) -> bool:
    is_user_community_owner: list = ModelUtilities.get_model_filter(
        Members,
        {
            'community_id': community_id,
            'member_id': user_id,
            'is_owner': True
        }
    )

    if not is_user_community_owner:
        message: str = f'user does not have permission to delete community, ' \
                       f'user_id: {user_id}, ' \
                       f'community_id: {community_id}'
        print(message)
        return False

    return True


def add_community_members_to_community_user_delete(community_id: int) -> None:
    print('adding community members to communityuserdelete table...')

    community_members: list = ModelUtilities.get_model_filter(
        Members,
        {
            'community_id': community_id
        }
    ).select_related(
        'member_id'
    )

    for member in community_members:
        member_id: int = member.member_id
        CommunityUserDelete.create_instance(
            {
                'user_instance': member_id,
                'community_id': community_id
            }
        )

    print('added community members to communityuserdelete table...')


def delete_community_preview_cache(community_id: int) -> None:
    print('deleting community preview cache keys...')

    community_preview_conversation_ids: list = ModelUtilities.get_model_filter(
        card_answers,
        {
            'preview_community': community_id
        }
    ).values_list(
        'id',
        flat=True
    )

    for community_preview_conversation_id in community_preview_conversation_ids:
        community_preview_cache_key: str = f'COMMUNITY_PREVIEW_{community_preview_conversation_id}_{community_id}'
        cache_ket_delete_status: bool = CacheImpl.delete_key(community_preview_cache_key)
        print(f'deleted key: {community_preview_cache_key}, status: {cache_ket_delete_status}')

    print('deleted community preview cache keys...')


def delete_chatroom_previews(community_id: int) -> None:
    print('deleting community preview chatrooms...')

    community_chatroom_list: list = ModelUtilities.get_model_filter(
        Collabcard,
        {
            'preview_community': community_id
        }
    ).values_list(
        'id',
        flat=True
    )

    if community_chatroom_list:
        delete_from_collabcard(community_id)
        update_collabcard_state(community_chatroom_list)

    print('deleted community preview chatrooms...')


def delete_from_collabcard(community_id: int) -> None:
    ModelUtilities.get_model_filter(
        Collabcard,
        {
            'preview_community': community_id
        }
    ).update(
        is_deleted=True,
        preview_type=None,
        internal_link=None,
        deleted_by_user=F('user'))


def update_collabcard_state(chatroom_list: list) -> None:
    ModelUtilities.get_model_filter(
        collabcardState,
        {
            'card__in': chatroom_list
        }
    ).update(
        updated_at=TimeUtilities.current_time_in_sec()
    )


def delete_conversation_previews(community_id: int) -> None:
    print('deleting community preview conversations...')

    ModelUtilities.get_model_filter(
        card_answers,
        {
            'preview_community': community_id
        }
    ).update(
        preview_type=None,
        internal_link=None,
        deleted_by_user=F('user'),
        last_updated=TimeUtilities.current_time_in_milliseconds()
    )

    print('deleted community preview conversations...')


def delete_community_instance(community_id: int) -> None:
    print('deleting community instance...')

    ModelUtilities.delete_record_in_model(
        Community,
        {
            'id': community_id
        }
    )

    print('deleted community instance...')


def run() -> None:
    delete_community_id: int = '<delete_community_id>'
    deleted_by_user_id: int = '<deleted_by_user_id>'

    print(f'starting community delete at {datetime.datetime.now()}...')
    print(f'deleting community, id: {delete_community_id}')
    print(f'deleted by user, id: {deleted_by_user_id}')

    delete_community(delete_community_id, deleted_by_user_id)
