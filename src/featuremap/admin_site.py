from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy, path

from .admin_import import PlaceImportUploadView, PlaceImportConfigView, PlaceImportConfirmView

class PlaceDbAdminSite(admin.AdminSite):
    site_header = _('PlaceDB Admin')
    site_title = _('PlaceDB Admin')
    site_url = reverse_lazy('featuremap:map')

    def get_admin_view(self, view_class):
        return view_class.as_view(
            admin_site = self,
        )

    def get_urls(self):
        urls = super().get_urls()
        urls.extend([
            path('import/place/', self.get_admin_view(PlaceImportUploadView), name='place_import'),
            path('import/place/<source_id>/config/', self.get_admin_view(PlaceImportConfigView), name='place_import_config'),
            path('import/place/<source_id>/confirm/', self.get_admin_view(PlaceImportConfirmView), name='place_import_confirm'), 
        ])
        return urls
    
admin_site = PlaceDbAdminSite(name='admin')