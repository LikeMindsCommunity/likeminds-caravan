from django.urls import path, include
from .views import *

urlpatterns = [
    #data_dashboard
    # path('dashboard', dashboard, name="dashboard"),
    # path('dashboard_weekly', dashboard_weekly, name="dashboard_weekly"),
    #
    # #community_types
    # path('list_community_types', list_community_types, name="list_community_types"),
    # path('add_community_types', add_community_types, name="add_community_types"),
    # path('edit_community_types/<community_type_id>', edit_community_types, name='edit_community_types'),
    #
    # #community_sub_types
    # path('list_community_subtypes', list_community_subtypes, name="list_community_subtypes"),
    # path('add_community_subtypes', add_community_subtypes, name="add_community_subtypes"),
    # path('edit_community_subtypes/<community_subtype_id>', edit_community_subtypes, name='edit_community_subtypes'),
    #
    # #community_field_type
    # path('list_community_fields', list_community_fields, name="list_community_fields"),
    # path('add_community_fields', add_community_fields, name="add_community_fields"),
    # path('edit_community_fields/<community_field_id>', edit_community_fields, name='edit_community_fields'),
    #
    # #answers
    # path('list_new_answers', list_new_answers, name="list_new_answers"),
    # path('list_all_answers', list_all_answers, name="list_all_answers"),
    #
    # #tools
    # path('url_shortner', url_shortner, name="url_shortner"),
    path('automate_message', MessageTemplateForOwner.as_view(), name="automate_message"),
    path('banner/', include('cms.marketing_banner.urls')),
    path('options/', include('cms.lm_options.urls')),
    path('app_review/', include('cms.in_app_review.urls'))
]
