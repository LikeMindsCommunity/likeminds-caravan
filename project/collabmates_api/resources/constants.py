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

RESOURCE_CATEGORY_ELEMENT = 'resource_category'
RESOURCE_ELEMENT = 'resource'

RESOURCE_CATEGORY_CREATION_EVENT = 'Resource category added'
RESOURCE_CATEGORY_VIEW_TYPE_UPDATION_EVENT = 'Display type changed'
RESOURCE_PERMISSION_UPDATION_EVENT = 'Permission edited'
RESOURCE_CATEGORY_EDITED_EVENT = 'Resource Category edited'
RESOURCE_EDITED_EVENT = 'Resource edited'
RESOURCE_ADDED_EVENT = 'Resource added'
RESOURCE_DELETED_EVENT = 'Resource deleted'
