from django.urls import path

from .banner_views_impl import (FetchBannerForCMSView, CreateOrUpdateBannerView,
                                CheckBannerView, RemoveBannerView, GetUriForUpload)

urlpatterns = [
    path('fetch', FetchBannerForCMSView.as_view(), name="fetch_banner_for_cms"),
    path('submit', CreateOrUpdateBannerView.as_view(), name="create_or_update_banner"),
    path('remove', RemoveBannerView.as_view(), name="remove_banner"),
    path('check', CheckBannerView.as_view(), name="check_banner"),
    path('upload_uri', GetUriForUpload.as_view(), name="upload_uri"),
]
