from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig

class FeaturemapConfig(AppConfig):
    name = 'featuremap'

class PlaceDbAdminConfig(AdminConfig):
    default_site = 'featuremap.admin.PlaceDbAdminSite'
