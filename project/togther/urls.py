from django.urls import path, include
from . import views

LOGIN_URL = 'login'
LOGOUT_URL = 'logout'
LOGIN_REDIRECT_URL = 'home'

urlpatterns = [
    path('', views.home, name="home"),
    path('dashboard/', views.dashboard, name="dashboard"),
    path('dashboard/recieved_requests', views.recieved_requests, name="recieved_requests"),
    path('community/join', views.join_request,name="join"),
    path('community/<int:community_id>/', views.community, name="community"),
    path('creategroup/', views.creategroup, name="create"),
    path('profile/<int:user_id>', views.profile, name="profile"),
    path('request_response', views.request_response, name="request_response"),
    
]