from django.urls import path
from .views import *

urlpatterns = [
    path('', dashboard, name="admin_dashboard"),
    path('update_form/<int:community_id>', update_form, name='update_form'),
    path('community_delete/<int:community_id>',community_delete,name='community_delete'),
    path('add_dashboard_admin/<int:community_id>',add_dashboard_admin,name='add_dashboard_admin'),
    path('add_dashboard_member/<int:community_id>',add_dashboard_member,name='add_dashboard_member'),
    path('show_pending_member/<int:community_id>',show_pending_members,name='show_pending_member'),
    path('aprove_member/<int:community_id>/<int:member_id>',aprove_member,name='aprove_member'),
    path('decline_member/<int:community_id>/<int:member_id>', decline_member, name='decline_member'),
    path('show_tags/<int:community_id>', show_tags, name='show_tags'),
    path('add_tags',add_tags,name='add_tags')

]
