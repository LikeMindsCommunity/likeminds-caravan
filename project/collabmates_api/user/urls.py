from django.urls import path
from collabmates_api.user.view_impl import DeleteUserView

urlpatterns = [
    path('delete', DeleteUserView.as_view(), name="delete_user")

]
