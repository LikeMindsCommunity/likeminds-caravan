from django.urls import path
from collabmates_api.user.view_impl import DeleteUserView, \
    UserSeenSurvey, UserLogout, UserRemoveProfile


urlpatterns = [
    path('delete', DeleteUserView.as_view(), name="delete_user"),
    path('survey_seen', UserSeenSurvey.as_view(), name="survey_seen"),
    path('logout', UserLogout.as_view(), name="logout"),
    path('remove_profile', UserRemoveProfile.as_view(), name="remove_profile")

]
