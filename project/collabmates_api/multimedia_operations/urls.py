from django.urls import path
from collabmates_api.multimedia_operations.views_impl import ViewsImpl

urlpatterns = [
    path('generate_presigned_post/', ViewsImpl.generate_presigned_post, name="generate_presigned_post"),
]
