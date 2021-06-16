from django.urls import path
from collabmates_api.user.view_impl import (DeleteUserView, UserSeenSurvey, UserLogout,
                                            UserRemoveProfile, UserLoginView, FetchUserAccess)


urlpatterns = [
    path('delete', DeleteUserView.as_view(), name="delete_user"),
    path('survey_seen', UserSeenSurvey.as_view(), name="survey_seen"),
    path('logout', UserLogout.as_view(), name="logout"),
    path('remove_profile', UserRemoveProfile.as_view(), name="remove_profile"),
    path('login', UserLoginView.as_view(), name="login"),
    path('fetch_app_access', FetchUserAccess.as_view(), name="fetch_app_access")
]
