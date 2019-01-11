from django.urls import path, include
from . import views
from collabmates_api import views as api_views

urlpatterns = [
    path('/communities', api_views.communities, name="communities"),
    path('/your_communities/<int:user_id>', api_views.your_communities, name="your_communities"),
]