from django.urls import path, include
from . import views

urlpatterns = [ 
    # path('login/', views.home, name="home"),
    path('signup/', views.signup, name="signup"),
    path('privacy/', views.privacy, name="privacy"),
    path('terms/', views.terms, name="terms"),
    # path('communities/', views.dashboard, name="dashboard"),

    path('community/<int:community_id>', views.community, name="community"),
    path('community_questions/<str:params>', views.community_questions, name="community_questions"),

    path('logout',views.logout_view, name = "logout_view"),
    path('thankyou', views.thankyou, name="thankyou"),
    # path('collabcard/<int:card_id>', views.collabcard, name="card"),
    path('view_answers/<int:card_id>',views.view_answers,name = 'view_answers'),
    path('accept_admin/<int:community_id>',views.accept_admin,name='accept_admin'),
    path('', views.index, name='index'),
    path('create_message', views.create_message, name='create_message'),
    path('pending_list/<int:community_id>', views.pending_list, name='pending_list'),
    path('questions_responses', views.questions_responses, name='questions_responses'),
    path('onboarding', views.onboarding, name='onboarding'),
    path('onboarding_profession', views.onboarding_profession, name='onboarding_profession'),
    path('onboarding_interest', views.onboarding_interest, name='onboarding_interest'),
    path('access_page', views.access_page, name='access_page'),
    path('alpha_page', views.alpha_page, name='alpha_page'),
    path('refer_members/<int:community_id>', views.refer_members, name='refer_members'),
    path('update_user_info/<str:user_email>', views.update_user_info, name='update_user_info'),

    path('download_the_app', views.download_the_app, name='download_the_app'),
    path('members_directory/<int:community_id>', views.members_directory, name='members_directory'),
    path('member_profile', views.member_profile, name='member_profile'),
    path('update_email', views.update_email, name='update_email'),
    path('oauth/complete/linkedin-oauth2', views.linked_in_authentication, name='linked_in_authentication'),
    path('', include('collabmates_api.urls', namespace='api')),

    #new urls - to be shifted in cms later
    path('community_wise_details', views.community_wise_details, name='community_wise_details'),
]

