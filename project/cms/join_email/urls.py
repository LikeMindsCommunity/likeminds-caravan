from django.urls import path

from .join_email_views import AddJoinEmailView

urlpatterns = [
    path('add', AddJoinEmailView.as_view(), name="add_default_join_email"),
]
