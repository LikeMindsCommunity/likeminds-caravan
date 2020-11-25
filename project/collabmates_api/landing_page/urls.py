from django.urls import path
from collabmates_api.landing_page.views_impl import ViewsImpl

urlpatterns = [
    path('', ViewsImpl.get_member_communities, name="get_member_communities")
]
