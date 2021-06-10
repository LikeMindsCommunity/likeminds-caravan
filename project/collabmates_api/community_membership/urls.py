from django.urls import path
from .membership_views import FetchCommunityBenefits

urlpatterns = [
    path('fetch_community_benefits', FetchCommunityBenefits.as_view(), name="fetch_community_benefits"),
]
