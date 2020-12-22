from django.urls import path
from collabmates_api.conversation.view_conversation_impl import FetchConversation

urlpatterns = [
    path('fetch', FetchConversation.as_view(), name="fetch_conversation")

]
