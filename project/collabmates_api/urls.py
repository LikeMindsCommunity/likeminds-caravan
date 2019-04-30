from django.urls import path, include
from . import views
from collabmates_api import views as api_views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('/communities', api_views.communities, name="communities"),
    path('/your_communities/<int:user_id>', api_views.your_communities, name="your_communities"),
    path('/community/<int:community_id>', api_views.community, name="community"),
    path('/similar_communities/<int:community_id>', api_views.similar_community, name="similar_community"),
    path('/community/<int:community_id>/questions', api_views.join_community, name="join"),
    path('/join_community', views.join_community_responses, name="join_community_responses"),
    path('/categories', api_views.categories, name="categories"),
    path('/create_community', api_views.create_community, name="create_community"),
    path('/community/<str:category>', api_views.category_filter, name="category_filter"),
    path('/user/<int:user_id>', api_views.user, name="user"),
    path('/admins/<int:community_id>', api_views.admins, name="admins"),
    path('/members/<int:community_id>', api_views.members, name="members"),
    path('/create_collabcard', api_views.create_card, name="create_card"),
    path('/collabcard/<int:card_id>', api_views.collabcard, name="collabcard"),
    path('/community_collabcard/<int:community_id>', api_views.community_cards, name="community_cards"),
    path('/create_answer', api_views.create_answer, name="create_answer"),
    path('/login',api_views.login,name = 'login'),
    path('/image_upload',api_views.image_upload,name = 'image'),
    path('/create_admin',api_views.create_admin,name = 'create_admin'),
    path('/pending_members/<int:community_id>',api_views.pending_members,name = 'pending_members'),
    path('/join',api_views.request_response,name = 'join'),
    path('/pending_members_count/<int:community_id>',api_views.pending_request_count,name = 'pending_request_count'),
    path('/collabcard_seen', api_views.collabcard_seen, name='collabcard_seen')
]