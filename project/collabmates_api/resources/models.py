import uuid
from django.db import models
from django.contrib.auth.models import User

from django.utils.translation import gettext_lazy as _
from utility.time_utilities import TimeUtilities

from togther.models import Community, Cohort


class ResourceSettings(models.Model):
    """Model for saving Resource Settings for a Community"""

    DAY_OF_WEEKLY_EMAIL_CHOICES = [0, 1, 2, 3, 4, 5, 6]
    TIME_OF_WEEKLY_EMAIL_CHOICES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
                                    13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]

    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True
    )
    community_id = models.ForeignKey(
        Community,
        editable=False,
        on_delete=models.PROTECT
    )
    day_of_weekly_email = models.IntegerField(
        choices=DAY_OF_WEEKLY_EMAIL_CHOICES
    )
    time_of_weekly_email = models.IntegerField(
        choices=TIME_OF_WEEKLY_EMAIL_CHOICES
    )
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Resource Setting'
        verbose_name_plural = 'Resource Settings'
        db_table = 'togther_resource_settings'

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(ResourceSettings, self).save(*args, **kwargs)


class ResourceCategory(models.Model):
    """Model for saving Resource Category in a Community"""

    VIEW_TYPE_CHOICES = [1, 2]

    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True
    )
    parent_category_id = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        help_text=_(
            'Stores pk of parent category id'
        )
    )
    community_id = models.ForeignKey(
        Community,
        on_delete=models.PROTECT
    )
    title = models.CharField(
        max_length=500
    )
    icon_url = models.TextField()
    banner_url = models.TextField(
        null=True,
        blank=True
    )
    view_type = models.IntegerField(
        default=1,
        choices=VIEW_TYPE_CHOICES,
        help_text=_(
            '1 - grid view, 2 - list view'
        )
    )
    is_deleted = models.BooleanField(
        default=False
    )
    is_downloadable = models.BooleanField(
        default=True
    )
    is_pinned = models.BooleanField(
        default=False
    )
    level = models.IntegerField(
        null=True,
        blank=True,
        help_text=_(
            'stores distance from root folder | root folder - 0'
        )
    )
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Resource Category'
        verbose_name_plural = 'Resource Categorys'
        db_table = 'togther_resource_category'

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(ResourceCategory, self).save(*args, **kwargs)


class ResourceCategoryPermission(models.Model):
    """Model to save resource category permissions"""

    ACCESS_TYPE_CHOICES = [1, 2, 3]

    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True
    )
    cohort_id = models.ForeignKey(
        Cohort,
        on_delete=models.PROTECT
    )
    category_id = models.ForeignKey(
        ResourceCategory,
        on_delete=models.PROTECT
    )
    access_type = models.IntegerField(
        default=1,
        choices=ACCESS_TYPE_CHOICES,
        help_text=_(
            '1 - access, 2 - restricted access, 3 - no access'
        )
    )
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Resource Category Permission'
        verbose_name_plural = 'Resource Category Permissions'
        db_table = 'togther_resource_category_permission'

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(ResourceCategoryPermission, self).save(*args, **kwargs)


class ResourceURL(models.Model):
    """Model for saving Resource URL in a Resource Category"""

    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True
    )
    category_id = models.ForeignKey(
        ResourceCategory,
        on_delete=models.PROTECT,
        help_text=_(
            'Stores pk of parent category id'
        )
    )
    url = models.TextField()
    og_tags = models.TextField(
        null=True,
        blank=True
    )
    is_deleted = models.BooleanField(
        default=False
    )
    is_downloadable = models.BooleanField(
        default=True
    )
    is_pinned = models.BooleanField(
        default=False
    )
    level = models.IntegerField(
        null=True,
        blank=True,
        help_text=_(
            'stores distance from root folder | root folder - 0'
        )
    )
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Resource URL'
        verbose_name_plural = 'Resource URLs'
        db_table = 'togther_resource_url'

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(ResourceURL, self).save(*args, **kwargs)


class ResourceURLPermission(models.Model):
    """Model to save resource URL permissions"""

    ACCESS_TYPE_CHOICES = [1, 2, 3]

    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True
    )
    cohort_id = models.ForeignKey(
        Cohort,
        on_delete=models.PROTECT
    )
    url_id = models.ForeignKey(
        ResourceURL,
        on_delete=models.PROTECT
    )
    access_type = models.IntegerField(
        default=1,
        choices=ACCESS_TYPE_CHOICES,
        help_text=_(
            '1 - access, 2 - restricted access, 3 - no access'
        )
    )
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Resource URL Permission'
        verbose_name_plural = 'Resource URL Permissions'
        db_table = 'togther_resource_url_permission'

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(ResourceURLPermission, self).save(*args, **kwargs)


class ResourceURLState(models.Model):
    """Model to save resource URL state for each member"""

    ACCESS_TYPE_CHOICES = [1, 2, 3]

    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True
    )
    user_id = models.ForeignKey(
        User,
        on_delete=models.PROTECT
    )
    url_id = models.ForeignKey(
        ResourceURL,
        on_delete=models.PROTECT
    )
    state = models.IntegerField(
        default=1,
        choices=ACCESS_TYPE_CHOICES,
        help_text=_(
            '1 - un-seen, 2 - seen, 3 - continue reading'
        )
    )
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Resource URL State'
        verbose_name_plural = 'Resource URL States'
        db_table = 'togther_resource_url_state'

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(ResourceURLState, self).save(*args, **kwargs)


class ResourceFile(models.Model):
    """Model for saving Resource File in a Resource Category"""

    TYPE_CHOICES = (
        ('pdf', 'pdf'),
    )

    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True
    )
    category_id = models.ForeignKey(
        ResourceCategory,
        on_delete=models.PROTECT,
        help_text=_(
            'Stores pk of parent category id'
        )
    )
    url = models.TextField()
    name = models.CharField(
        max_length=500
    )
    meta = models.TextField(
        null=True,
        blank=True
    )
    type = models.CharField(
        max_length=15,
        choices=TYPE_CHOICES
    )
    is_deleted = models.BooleanField(
        default=False
    )
    is_downloadable = models.BooleanField(
        default=True
    )
    is_pinned = models.BooleanField(
        default=False
    )
    level = models.IntegerField(
        null=True,
        blank=True,
        help_text=_(
            'stores distance from root folder | root folder - 0'
        )
    )
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Resource File'
        verbose_name_plural = 'Resource Files'
        db_table = 'togther_resource_file'

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(ResourceFile, self).save(*args, **kwargs)


class ResourceFilePermission(models.Model):
    """Model to save resource File permissions"""

    ACCESS_TYPE_CHOICES = [1, 2, 3]

    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True
    )
    cohort_id = models.ForeignKey(
        Cohort,
        on_delete=models.PROTECT
    )
    file_id = models.ForeignKey(
        ResourceFile,
        on_delete=models.PROTECT
    )
    access_type = models.IntegerField(
        default=1,
        choices=ACCESS_TYPE_CHOICES,
        help_text=_(
            '1 - access, 2 - restricted access, 3 - no access'
        )
    )
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Resource File Permission'
        verbose_name_plural = 'Resource File Permissions'
        db_table = 'togther_resource_file_permission'

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(ResourceFilePermission, self).save(*args, **kwargs)


class ResourceFileState(models.Model):
    """Model to save resource File state for each member"""

    ACCESS_TYPE_CHOICES = [1, 2, 3]

    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True
    )
    user_id = models.ForeignKey(
        User,
        on_delete=models.PROTECT
    )
    file_id = models.ForeignKey(
        ResourceFile,
        on_delete=models.PROTECT
    )
    state = models.IntegerField(
        default=1,
        choices=ACCESS_TYPE_CHOICES,
        help_text=_(
            '1 - un-seen, 2 - seen, 3 - continue reading'
        )
    )
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Resource File State'
        verbose_name_plural = 'Resource File States'
        db_table = 'togther_resource_file_state'

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(ResourceFileState, self).save(*args, **kwargs)


class ResourceReference(models.Model):
    """Model to save resource references for each resource pair"""

    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True
    )
    category_id = models.ForeignKey(
        ResourceCategory,
        on_delete=models.PROTECT
    )
    url_id = models.ForeignKey(
        ResourceURL,
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )
    file_id = models.ForeignKey(
        ResourceFile,
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )
    child_category_id = models.ForeignKey(
        ResourceCategory,
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Resource Reference'
        verbose_name_plural = 'Resource References'
        db_table = 'togther_resource_reference'

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(ResourceReference, self).save(*args, **kwargs)


class ResourceCategoryParentCategory(models.Model):
    """Model to save references among parent and child categories"""

    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True
    )
    category_id = models.ForeignKey(
        ResourceCategory,
        on_delete=models.PROTECT
    )
    child_category_id = models.ForeignKey(
        ResourceCategory,
        on_delete=models.PROTECT
    )
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Resource Category Parent Category'
        verbose_name_plural = 'Resource Category Parent Categories'
        db_table = 'togther_resource_category_parent_category'

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(ResourceCategoryParentCategory, self).save(*args, **kwargs)


class ResourceURLParentCategory(models.Model):
    """Model to save references among parent category and child url"""

    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True
    )
    category_id = models.ForeignKey(
        ResourceCategory,
        on_delete=models.PROTECT
    )
    url_id = models.ForeignKey(
        ResourceURL,
        on_delete=models.PROTECT
    )
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Resource URL Parent Category'
        verbose_name_plural = 'Resource URL Parent Categories'
        db_table = 'togther_resource_url_parent_category'

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(ResourceURLParentCategory, self).save(*args, **kwargs)


class ResourceFileParentCategory(models.Model):
    """Model to save references among parent category and child file"""

    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True
    )
    category_id = models.ForeignKey(
        ResourceCategory,
        on_delete=models.PROTECT
    )
    file_id = models.ForeignKey(
        ResourceFile,
        on_delete=models.PROTECT
    )
    created_at = models.BigIntegerField(default=0)
    updated_at = models.BigIntegerField(default=0)

    class Meta:
        verbose_name = 'Resource File Parent Category'
        verbose_name_plural = 'Resource file Parent Categories'
        db_table = 'togther_resource_file_parent_category'

    def save(self, *args, **kwargs):

        current_time_in_ms = TimeUtilities.current_time_in_milliseconds()

        if self.created_at == 0:
            self.created_at = current_time_in_ms

        self.updated_at = current_time_in_ms

        super(ResourceFileParentCategory, self).save(*args, **kwargs)
