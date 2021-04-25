from django.contrib.admin.apps import AdminConfig

class PlaceDbAdminConfig(AdminConfig):
    default_site = 'featuremap.admin_site.PlaceDbAdminSite'