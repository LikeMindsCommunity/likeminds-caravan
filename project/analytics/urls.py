from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', dashboard, name="analytics_dashboard"),
    path('users',all_user,name='users'),
    path('members/<int:community_id>', all_members, name='analytics_members'),
    path('analytics', analytics, name='analytics_user'),
    path('analytics_community/<int:community_id>', analytics_community, name='community_analytics'),
    path('user_invited_members/<int:user_id>', user_invited_members, name='user_invited_members'),
    path('hidden_tags/<int:community_id>', hidden_tags, name='community_tags'),
    path('user_communities/<int:user_id>', user_communities, name='analytics_user_communities'),
    path('search/<str:tag_ids>', search, name='analytics_search'),
    path('update_user_tags/<int:user_id>', user_tags, name='analytics_user_tags'),

]
