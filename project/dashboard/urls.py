from django.urls import path
from .views import *

urlpatterns = [
    path('', dashboard, name="admin_dashboard"),
    path('update_form/<int:community_id>', update_form, name='update_form'),
    path('community_delete/<int:community_id>',community_delete,name='community_delete'),
    path('add_dashboard_admin/<int:community_id>',add_dashboard_admin,name='add_dashboard_admin')
]
