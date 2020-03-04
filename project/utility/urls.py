from django.urls import path, include
from utility import utils as api_views
from .community_type import community_type_view

urlpatterns = [
    path('city/<str:city>', api_views.get_city_address, name="city"),
    path('community_type/<str:community_id>',community_type_view, name="community_type"),
    path('community_type/<str:community_id>/type/<str:response_type>',community_type_view, name="community_type_1"),
]