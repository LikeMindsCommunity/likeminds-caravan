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
                                 VersionUtilities.PlatformCode.WEB,
                                 VersionUtilities.PlatformCode.REACT_NATIVE,
                                 VersionUtilities.PlatformCode.REACT,
                                 VersionUtilities.PlatformCode.FLUTTER]:
                platform_code = platform_code + '-sdk'

            return platform_code

    class SdkSource:
        CHAT = 'chat'
        FEED = 'feed'

    unreleased_version_code: int = 9999

    group_tags: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: unreleased_version_code,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: 367,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: unreleased_version_code,

            PlatformCode.ANDROID_SDK: 202,
            PlatformCode.FLUTTER_SDK: 1,
            PlatformCode.IOS_SDK: 362,
            PlatformCode.REACT_SDK: 22,
            PlatformCode.REACT_NATIVE_SDK: 9,
            PlatformCode.WEB_SDK: 22,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: 2, 
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    create_chatroom_revamp: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: unreleased_version_code,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: unreleased_version_code,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: 14,

            PlatformCode.ANDROID_SDK: 207,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: 14,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: 14,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    create_conversation_revamp: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: 213,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: 374,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: 16,

            PlatformCode.ANDROID_SDK: 207,
            PlatformCode.FLUTTER_SDK: 1,
            PlatformCode.IOS_SDK: 372,
            PlatformCode.REACT_SDK: 21,
            PlatformCode.REACT_NATIVE_SDK: 4,
            PlatformCode.WEB_SDK: 16,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    m2cm_v2: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: unreleased_version_code,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: unreleased_version_code,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: unreleased_version_code,

            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: 15,
            PlatformCode.REACT_NATIVE_SDK: 7,
            PlatformCode.WEB_SDK: 15,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    participants_meta_pagination: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: unreleased_version_code,
            PlatformCode.FLUTTER: unreleased_version_code, 
            PlatformCode.IOS: 373,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: 1,
            PlatformCode.WEB: 17,

            PlatformCode.ANDROID_SDK: 210,
            PlatformCode.FLUTTER_SDK: 1,
            PlatformCode.IOS_SDK: 371,
            PlatformCode.REACT_SDK: 17,
            PlatformCode.REACT_NATIVE_SDK: 1,
            PlatformCode.WEB_SDK: 17,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    members_meta_pagination_and_search: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: unreleased_version_code,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: unreleased_version_code,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: unreleased_version_code,

            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: 1,
            PlatformCode.FLUTTER_SDK: 2,
            PlatformCode.IOS_SDK: 1,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    invite_settings: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: 190,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: 360,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: unreleased_version_code,

            PlatformCode.ANDROID_SDK: 190,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: 360,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: 16,
            PlatformCode.WEB_SDK: unreleased_version_code,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    feed_member_rights: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: unreleased_version_code,
            PlatformCode.FLUTTER: unreleased_version_code, 
            PlatformCode.IOS: unreleased_version_code,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: unreleased_version_code,

            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code, 
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: 15,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: 2,
            PlatformCode.FLUTTER_SDK: 1, 
            PlatformCode.IOS_SDK: 1,
            PlatformCode.REACT_SDK: 1,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    chatroom_invite: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: unreleased_version_code,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: unreleased_version_code,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: unreleased_version_code,

            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: 15,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    community_join_form: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: unreleased_version_code,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: unreleased_version_code,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: unreleased_version_code,

            PlatformCode.ANDROID_SDK: 211,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: 374,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: 4,
            PlatformCode.WEB_SDK: unreleased_version_code,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    tag_only_participants: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: unreleased_version_code,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: unreleased_version_code,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: unreleased_version_code,

            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    fetch_reports_pagination_and_filter: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: unreleased_version_code,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: unreleased_version_code,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: unreleased_version_code,

            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: 19,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    fetch_all_chatrooms: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: unreleased_version_code,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: unreleased_version_code,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: unreleased_version_code,

            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    community_feed_date_uniform: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: unreleased_version_code,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: unreleased_version_code,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: unreleased_version_code,

            PlatformCode.ANDROID_SDK: 300,
            PlatformCode.FLUTTER_SDK: 3,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    create_intro_room: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: unreleased_version_code,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: unreleased_version_code,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: unreleased_version_code,

            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    new_chatroom_settings: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: unreleased_version_code,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: unreleased_version_code,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: unreleased_version_code,

            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    community_hood: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: 1000,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: 1000,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: 1000,

            PlatformCode.ANDROID_SDK: 1000,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: 1000,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: 1000,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: 1000,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: 1000,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: 1000,
        }
    }

    alias_question: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: unreleased_version_code,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: unreleased_version_code,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: unreleased_version_code,

            PlatformCode.ANDROID_SDK: 188,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: 360,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: unreleased_version_code,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    participants_meta_without_pagination: dict = {
        SdkSource.CHAT: {
            PlatformCode.ANDROID: 1000,
            PlatformCode.FLUTTER: unreleased_version_code,
            PlatformCode.IOS: unreleased_version_code,
            PlatformCode.REACT: unreleased_version_code,
            PlatformCode.REACT_NATIVE: unreleased_version_code,
            PlatformCode.WEB: unreleased_version_code,

            PlatformCode.ANDROID_SDK: 1000,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        },
        SdkSource.FEED: {
            PlatformCode.ANDROID_SDK: 1000,
            PlatformCode.FLUTTER_SDK: unreleased_version_code,
            PlatformCode.IOS_SDK: unreleased_version_code,
            PlatformCode.REACT_SDK: unreleased_version_code,
            PlatformCode.REACT_NATIVE_SDK: unreleased_version_code,
            PlatformCode.WEB_SDK: unreleased_version_code,
        }
    }

    @staticmethod
    def check_version(platform_code: str, version_code: int, feature_version_dict: dict,
                      sdk_source: str = None) -> bool:
        """
        returns True if,
          version code >= feature_version_code for the given platform
        returns False for all other cases
        """

        if not type(version_code) == int:
            return False

        if not type(platform_code) == str:
            return False
        
        if not sdk_source:
            if platform_code in [VersionUtilities.PlatformCode.FLUTTER_SDK, VersionUtilities.PlatformCode.FLUTTER]:
                sdk_source = VersionUtilities.SdkSource.FEED   
            else:     
                sdk_source = VersionUtilities.SdkSource.CHAT

        if not type(sdk_source) == str:
            return False

        if not feature_version_dict.get(sdk_source, None):
            return False

        if not feature_version_dict[sdk_source].get(platform_code, None):
            return False

        return version_code >= feature_version_dict[sdk_source][platform_code]
    
    @staticmethod
    def api_revamp_v1_check(accept_version:str = "") -> bool:
        """
        returns True if accept_version == v1
        """

        return accept_version == 'v1'
