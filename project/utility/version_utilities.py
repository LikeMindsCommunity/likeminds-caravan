class VersionUtilities:

    class PlatformCode:
        ANDROID = 'an'
        IOS = 'ios'
        WEB = 'web'
        FLUTTER = 'fl'
        REACT_NATIVE = 'rn'
        REACT = 'rt'
        ANDROID_SDK = 'an-sdk'
        IOS_SDK = 'ios-sdk'
        WEB_SDK = 'web-sdk'
        FLUTTER_SDK = 'fl-sdk'
        REACT_NATIVE_SDK = 'rn-sdk'
        REACT_SDK = 'rt-sdk'

        @staticmethod
        def convert_platform_code_to_sdk(platform_code):
            if platform_code in [VersionUtilities.PlatformCode.IOS,
                                 VersionUtilities.PlatformCode.ANDROID,
                                 VersionUtilities.PlatformCode.WEB]:
                platform_code = platform_code + '-sdk'

            return platform_code

    unreleased_version_code: int = 9999

    group_tags: dict = {
        PlatformCode.ANDROID: unreleased_version_code,
        PlatformCode.IOS: 367,
        PlatformCode.WEB: unreleased_version_code,
        PlatformCode.ANDROID_SDK: 202,
        PlatformCode.IOS_SDK: 362,
        PlatformCode.WEB_SDK: unreleased_version_code,
        PlatformCode.FLUTTER: 2,
        PlatformCode.REACT_NATIVE: unreleased_version_code,
        PlatformCode.FLUTTER_SDK: 2,
        PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
        PlatformCode.REACT: unreleased_version_code,
        PlatformCode.REACT_SDK: unreleased_version_code,
    }

    create_chatroom_revamp: dict = {
        PlatformCode.ANDROID: unreleased_version_code,
        PlatformCode.IOS: unreleased_version_code,
        PlatformCode.WEB: 14,
        PlatformCode.ANDROID_SDK: 207,
        PlatformCode.IOS_SDK: unreleased_version_code,
        PlatformCode.WEB_SDK: 14,
        PlatformCode.FLUTTER: 1,
        PlatformCode.REACT_NATIVE: 1,
        PlatformCode.FLUTTER_SDK: 1,
        PlatformCode.REACT_NATIVE_SDK: 1,
        PlatformCode.REACT: unreleased_version_code,
        PlatformCode.REACT_SDK: 14,
    }

    create_conversation_revamp: dict = {
        PlatformCode.ANDROID: 213,
        PlatformCode.IOS: 374,
        PlatformCode.WEB: 16,
        PlatformCode.ANDROID_SDK: 207,
        PlatformCode.IOS_SDK: 372,
        PlatformCode.WEB_SDK: 16,
        PlatformCode.FLUTTER: unreleased_version_code,
        PlatformCode.REACT_NATIVE: unreleased_version_code,
        PlatformCode.FLUTTER_SDK: unreleased_version_code,
        PlatformCode.REACT_NATIVE_SDK: 4,
        PlatformCode.REACT: unreleased_version_code,
        PlatformCode.REACT_SDK: 21,
    }

    m2cm_v2: dict = {
        PlatformCode.ANDROID: unreleased_version_code,
        PlatformCode.IOS: unreleased_version_code,
        PlatformCode.WEB: unreleased_version_code,
        PlatformCode.ANDROID_SDK: unreleased_version_code,
        PlatformCode.IOS_SDK: unreleased_version_code,
        PlatformCode.WEB_SDK: 15,
        PlatformCode.FLUTTER: unreleased_version_code,
        PlatformCode.REACT_NATIVE: unreleased_version_code,
        PlatformCode.FLUTTER_SDK: unreleased_version_code,
        PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
        PlatformCode.REACT: unreleased_version_code,
        PlatformCode.REACT_SDK: 15,
    }

    participants_meta_pagination: dict = {
        PlatformCode.ANDROID: 214,
        PlatformCode.IOS: 373,
        PlatformCode.WEB: 17,
        PlatformCode.ANDROID_SDK: 210,
        PlatformCode.IOS_SDK: 371,
        PlatformCode.WEB_SDK: 17,
        PlatformCode.FLUTTER: 1,
        PlatformCode.REACT_NATIVE: 1,
        PlatformCode.FLUTTER_SDK: 1,
        PlatformCode.REACT_NATIVE_SDK: 1,
        PlatformCode.REACT: unreleased_version_code,
        PlatformCode.REACT_SDK: 17,
    }

    members_meta_pagination_and_search: dict = {
        PlatformCode.ANDROID: unreleased_version_code,
        PlatformCode.IOS: unreleased_version_code,
        PlatformCode.WEB: unreleased_version_code,
        PlatformCode.ANDROID_SDK: 1,
        PlatformCode.IOS_SDK: unreleased_version_code,
        PlatformCode.WEB_SDK: unreleased_version_code,
        PlatformCode.FLUTTER: 2,
        PlatformCode.REACT_NATIVE: unreleased_version_code,
        PlatformCode.FLUTTER_SDK: 2,
        PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
        PlatformCode.REACT: unreleased_version_code,
        PlatformCode.REACT_SDK: unreleased_version_code,
    }

    invite_settings: dict = {
        PlatformCode.ANDROID: 190,
        PlatformCode.IOS: 360,
        PlatformCode.WEB: unreleased_version_code,
        PlatformCode.ANDROID_SDK: 190,
        PlatformCode.IOS_SDK: 360,
        PlatformCode.WEB_SDK: unreleased_version_code,
        PlatformCode.FLUTTER: 1,
        PlatformCode.REACT_NATIVE: 1,
        PlatformCode.FLUTTER_SDK: 1,
        PlatformCode.REACT_NATIVE_SDK: 1,
        PlatformCode.REACT: unreleased_version_code,
        PlatformCode.REACT_SDK: unreleased_version_code,
    }

    feed_member_rights: dict = {
        PlatformCode.ANDROID: unreleased_version_code,
        PlatformCode.IOS: unreleased_version_code,
        PlatformCode.WEB: unreleased_version_code,
        PlatformCode.ANDROID_SDK: unreleased_version_code,
        PlatformCode.IOS_SDK: unreleased_version_code,
        PlatformCode.WEB_SDK: 15,
        PlatformCode.FLUTTER: 1,
        PlatformCode.REACT_NATIVE: unreleased_version_code,
        PlatformCode.FLUTTER_SDK: 1,
        PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
        PlatformCode.REACT: unreleased_version_code,
        PlatformCode.REACT_SDK: 15,
    }

    chatroom_invite: dict = {
        PlatformCode.ANDROID: unreleased_version_code,
        PlatformCode.IOS: unreleased_version_code,
        PlatformCode.WEB: unreleased_version_code,
        PlatformCode.ANDROID_SDK: unreleased_version_code,
        PlatformCode.IOS_SDK: unreleased_version_code,
        PlatformCode.WEB_SDK: 15,
        PlatformCode.FLUTTER: unreleased_version_code,
    }

    community_join_form: dict = {
        PlatformCode.ANDROID: unreleased_version_code,
        PlatformCode.IOS: unreleased_version_code,
        PlatformCode.WEB: unreleased_version_code,
        PlatformCode.ANDROID_SDK: 211,
        PlatformCode.IOS_SDK: 374,
        PlatformCode.WEB_SDK: unreleased_version_code,
        PlatformCode.FLUTTER: unreleased_version_code,
        PlatformCode.REACT_NATIVE: unreleased_version_code,
        PlatformCode.FLUTTER_SDK: unreleased_version_code,
        PlatformCode.REACT_NATIVE_SDK: 4,
        PlatformCode.REACT: unreleased_version_code,
        PlatformCode.REACT_SDK: unreleased_version_code,
    }

    tag_only_participants: dict = {
        PlatformCode.ANDROID: unreleased_version_code,
        PlatformCode.IOS: unreleased_version_code,
        PlatformCode.WEB: unreleased_version_code,
        PlatformCode.ANDROID_SDK: unreleased_version_code,
        PlatformCode.IOS_SDK: unreleased_version_code,
        PlatformCode.WEB_SDK: unreleased_version_code,
        PlatformCode.FLUTTER: unreleased_version_code,
        PlatformCode.REACT_NATIVE: unreleased_version_code,
        PlatformCode.FLUTTER_SDK: unreleased_version_code,
        PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
        PlatformCode.REACT: unreleased_version_code,
        PlatformCode.REACT_SDK: unreleased_version_code,
    }

    fetch_reports_pagination_and_filter: dict = {
        PlatformCode.ANDROID: unreleased_version_code,
        PlatformCode.IOS: unreleased_version_code,
        PlatformCode.WEB: unreleased_version_code,
        PlatformCode.ANDROID_SDK: unreleased_version_code,
        PlatformCode.IOS_SDK: unreleased_version_code,
        PlatformCode.WEB_SDK: unreleased_version_code,
        PlatformCode.FLUTTER: unreleased_version_code,
        PlatformCode.REACT_NATIVE: unreleased_version_code,
        PlatformCode.FLUTTER_SDK: unreleased_version_code,
        PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
        PlatformCode.REACT: unreleased_version_code,
        PlatformCode.REACT_SDK: unreleased_version_code,
    }

    fetch_all_chatrooms: dict = {
        PlatformCode.ANDROID: unreleased_version_code,
        PlatformCode.IOS: unreleased_version_code,
        PlatformCode.WEB: unreleased_version_code,
        PlatformCode.ANDROID_SDK: unreleased_version_code,
        PlatformCode.IOS_SDK: unreleased_version_code,
        PlatformCode.WEB_SDK: unreleased_version_code,
        PlatformCode.FLUTTER: unreleased_version_code,
        PlatformCode.REACT_NATIVE: unreleased_version_code,
        PlatformCode.FLUTTER_SDK: unreleased_version_code,
        PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
        PlatformCode.REACT: unreleased_version_code,
        PlatformCode.REACT_SDK: unreleased_version_code,
    }

    @staticmethod
    def check_version(platform_code: str, version_code: int, feature_version_dict: dict) -> bool:
        """
        returns True if,
          version code >= feature_version_code for the given platform
        returns False for all other cases
        """
        if not feature_version_dict.get(platform_code, None):
            return False

        if not type(version_code) == int:
            return False

        if not type(platform_code) == str:
            return False

        return version_code >= feature_version_dict[platform_code]
