from django.urls import path
from collabmates_api.community.community_view_impl import FetchCommunity

urlpatterns = [
    path('fetch', FetchCommunity.as_view(), name="fetch_community")

]

