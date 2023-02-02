class VersionUtilities:

    class PlatformCode:
        ANDROID = 'an'
        IOS = 'ios'
        WEB = 'web'
        ANDROID_SDK = 'an-sdk'
        IOS_SDK = 'ios-sdk'
        WEB_SDK = 'web-sdk'

        @staticmethod
        def convert_platform_code_to_sdk(platform_code):
            if platform_code in [VersionUtilities.PlatformCode.IOS,
                                 VersionUtilities.PlatformCode.ANDROID,
                                 VersionUtilities.PlatformCode.WEB]:
                platform_code = platform_code + '-sdk'

            return platform_code

    beta_dummy_version: int = 999

    group_tags: dict = {
        PlatformCode.ANDROID: beta_dummy_version,
        PlatformCode.IOS: 367,
        PlatformCode.WEB: beta_dummy_version,
        PlatformCode.ANDROID_SDK: 202,
        PlatformCode.IOS_SDK: 362,
        PlatformCode.WEB_SDK: beta_dummy_version
    }

    create_chatroom_revamp: dict = {
        PlatformCode.ANDROID: beta_dummy_version,
        PlatformCode.IOS: beta_dummy_version,
        PlatformCode.WEB: 14,
        PlatformCode.ANDROID_SDK: 207,
        PlatformCode.IOS_SDK: beta_dummy_version,
        PlatformCode.WEB_SDK: 14
    }

    create_conversation_revamp: dict = {
        PlatformCode.ANDROID: beta_dummy_version,
        PlatformCode.IOS: beta_dummy_version,
        PlatformCode.WEB: beta_dummy_version,
        PlatformCode.ANDROID_SDK: beta_dummy_version,
        PlatformCode.IOS_SDK: beta_dummy_version,
        PlatformCode.WEB_SDK: beta_dummy_version
    }

    m2cm_v2: dict = {
        PlatformCode.ANDROID: 1209,
        PlatformCode.IOS: 1209,
        PlatformCode.WEB: 1209,
        PlatformCode.ANDROID_SDK: 1209,
        PlatformCode.IOS_SDK: 1209,
        PlatformCode.WEB_SDK: 16
    }

    participants_meta_pagination: dict = {
        PlatformCode.ANDROID: 214,
        PlatformCode.IOS: 373,
        PlatformCode.WEB: 17,
        PlatformCode.ANDROID_SDK: 210,
        PlatformCode.IOS_SDK: 371,
        PlatformCode.WEB_SDK: 17
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
