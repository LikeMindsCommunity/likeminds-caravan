from django.urls import path, include
from . import views
from collabmates_api import views as api_views

urlpatterns = [
    path('/communities', api_views.communities, name="communities"),
    path('/your_communities/<int:user_id>', api_views.your_communities, name="your_communities"),
    path('/community/<int:community_id>', api_views.community, name="community"),
    path('/similar_communities/<int:community_id>', api_views.similar_community, name="similar_community"),
    path('/community/<int:community_id>/join', api_views.join_community, name="join"),
    path('/community/<str:category>', api_views.category_filter, name="category_filter"),
]