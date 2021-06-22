from django.urls import path
from .membership_views import FetchCommunityBenefits, RemoveCommunityMemberShipView, RenewCommunityMemberShipView

urlpatterns = [
    path('fetch_community_benefits', FetchCommunityBenefits.as_view(), name="fetch_community_benefits"),
    path('remove_member', RemoveCommunityMemberShipView.as_view(), name="remove_member"),
    path('renew_member', RenewCommunityMemberShipView.as_view(), name="renew_member"),
]
