from .models import ResourceCategoryPermission, ResourceFilePermission, ResourceURLPermission

FETCH_RESOURCE_CATEGORY_PAGE_SIZE = 50

class RESOURCE_STATE:
    UNSEEN = 1
    SEEN = 2
    CONTINUE_READING = 3

class RESOURCE_TYPE:
    CATEGORY = 'category'
    URL = 'url'
    FILE = 'file'
    CHILD_CATEGORY = 'child_category'

class RESOURCE_ACCESS_TYPE:
    FULL_ACCESS = 1
    RESTRICTED_ACCESS = 2
    NO_ACCESS = 3


RESOURCE_TYPE_TO_MODEL_MAPPER = {
    RESOURCE_TYPE.CATEGORY: {
        'model': ResourceCategoryPermission,
        'field': 'category_id'
    },
    RESOURCE_TYPE.URL: {
        'model': ResourceURLPermission,
        'field': 'url_id'
    },
    RESOURCE_TYPE.FILE: {
        'model': ResourceFilePermission,
        'field': 'file_id'
    }
}
