from django.urls import path
from collabmates_api.user.view_impl import (DeleteUserView, UserSeenSurvey, UserLogout,
                                            UserRemoveProfile, UserLoginView, FetchUserAccess, FetchDmHome,
                                            UpdateDmTutorial, FetchDmFeed, FetchAllUsers, BotView,
                                            FetchUser, WhatsappSubscriptionView)


urlpatterns = [
    path('delete', DeleteUserView.as_view(), name="delete_user"),
    path('survey_seen', UserSeenSurvey.as_view(), name="survey_seen"),
    path('logout', UserLogout.as_view(), name="logout"),
    path('remove_profile', UserRemoveProfile.as_view(), name="remove_profile"),
    path('login', UserLoginView.as_view(), name="login"),
    path('fetch_app_access', FetchUserAccess.as_view(), name="fetch_app_access"),
    path('fetch_dm_home', FetchDmHome.as_view(), name="fetch_dm_home"),
    path('update_dm_tutorial', UpdateDmTutorial.as_view(), name="update_dm_tutorial"),
    path('fetch_dm_feed', FetchDmFeed.as_view(), name="fetch_dm_feed"),
    path('fetch_all', FetchAllUsers.as_view(), name="fetch_all_users"),
    path('bot', BotView.as_view(), name="create_update_bot"),
    path('fetch', FetchUser.as_view(), name="fetch"),
    path('subscription/whatsapp', WhatsappSubscriptionView.as_view(), name="whatsapp_subscription")
]
