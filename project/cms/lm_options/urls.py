from django.urls import path

from .options_views import CreateOrUpdateOptionView, FetchOptionView

urlpatterns = [
    path('fetch', FetchOptionView.as_view(), name="fetch_option"),
    path('create', CreateOrUpdateOptionView.as_view(), name="create_or_update_option")
]
