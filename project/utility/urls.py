from django.urls import path, include
from utility import utils as api_views

urlpatterns = [
    path('city/<str:city>', api_views.get_city_address, name="city"),

]