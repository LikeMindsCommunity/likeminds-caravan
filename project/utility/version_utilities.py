class VersionUtilities:

    class PlatformCode:
        ANDROID = 'an'
        IOS = 'ios'
        WEB = 'web'
        ANDROID_SDK = 'an-sdk'
        IOS_SDK = 'ios-sdk'
        WEB_SDK = 'web-sdk'

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

    participants_meta_pagination: dict = {
        PlatformCode.ANDROID: beta_dummy_version,
        PlatformCode.IOS: beta_dummy_version,
        PlatformCode.WEB: beta_dummy_version,
        PlatformCode.ANDROID_SDK: beta_dummy_version,
        PlatformCode.IOS_SDK: beta_dummy_version,
        PlatformCode.WEB_SDK: beta_dummy_version
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
