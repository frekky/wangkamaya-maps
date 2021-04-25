from django.urls import path, register_converter, reverse_lazy
from django.views.generic.base import RedirectView
from django.contrib.auth import views as auth_views
from django.conf import settings

from featuremap import views
from featuremap.auth import token_login_view
from featuremap.admin import admin_site
from featuremap.apps import get_detail_url

app_name = 'featuremap'

urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy('featuremap:map'), permanent=True)),
    path('map/', views.leaflet_view, name='map'),

    path('data/', views.places_json, name='data'),
    path(get_detail_url() + '<int:place_id>/', views.place_detail, name='detail'),
    path('about/', views.AboutView.as_view(), name='about'),

    path('user/<login_token>/', token_login_view, name='map_login'),
]
