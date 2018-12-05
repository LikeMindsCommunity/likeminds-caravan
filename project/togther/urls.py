from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('dashboard/', views.dashboard, name="dashboard"),
    path('dashboard/<slug:data>', views.dashboard, name="dashboard"),
    path('dashboard/recieved_requests', views.recieved_requests, name="recieved_requests"),
    path('community/<int:community_id>/join', views.join_community, name="join_community"),
    path('community/join', views.join_request,name="join"),
    path('community/<int:community_id>/', views.community, name="community"),
    path('community/<int:community_id>/members_list', views.members_list, name="members_list"),
    path('creategroup/', views.creategroup, name="create"),
    path('profile/<int:user_id>', views.profile, name="profile"),
    path('profile/<int:user_id>/mycommunities', views.my_communities, name="my_communities"),
    path('profile/<int:user_id>/communities_as_admin', views.communities_as_admin, name="communities_as_admin"),
    path('request_response', views.request_response, name="request_response"),
    path('profile/<int:user_id>/edit',views.edit_profile, name = "edit_profile"),
    path('logout',views.logout_view, name = "logout_view"),
    path('creategroup/<int:community_id>/form_data',views.form_data,name='form_data'),
    path('thankyou', views.thankyou, name="thankyou"),
]