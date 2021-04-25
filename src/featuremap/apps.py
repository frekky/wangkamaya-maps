from django.apps import AppConfig
from django.core.checks import register, Tags
from django.conf import settings
from django.utils.translation import gettext as _

class FeaturemapConfig(AppConfig):
    name = 'featuremap'


# some configuration-getters: one place for default app-specific settings

def get_site_name():
    return getattr(settings, 'SITE_NAME', _('PlaceDB Map'))

def get_detail_url():
    return getattr(settings, 'DETAIL_URL', 'detail/')