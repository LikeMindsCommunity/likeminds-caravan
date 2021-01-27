from django.urls import path
from collabmates_api.snackbar.view_snackbar_impl import FetchSnackbar

urlpatterns = [
    path('fetch', FetchSnackbar.as_view(), name="fetch_snackbar")

]

