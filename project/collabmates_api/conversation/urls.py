from django.urls import path
from collabmates_api.conversation.view_conversation_impl import FethcConversation

urlpatterns = [
    path('fetch', FethcConversation.as_view(), name="fetch_conversation")

]
