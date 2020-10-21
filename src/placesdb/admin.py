from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy

class PlaceDbAdminSite(AdminSite):
    site_header = _('PlaceDB Admin')
    site_title = _('PlaceDB Admin')
    site_url = reverse_lazy('featuremap:map')

class PlaceDbAdminConfig(AdminConfig):
    default_site = 'placesdb.admin.PlaceDbAdminSite'
    
admin_site = PlaceDbAdminSite(name='admin')
