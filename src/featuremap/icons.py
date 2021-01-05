from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

import re
import random
import logging

logger = logging.getLogger(__name__)

_icons_dir = getattr(settings, 'ICONS_DIR', None)
if not _icons_dir:
    raise ImproperlyConfigured("ICONS_DIR must be configured in settings.py")

def clean_filename(f):
    f = re.sub(r'[^a-z0-9-.]', '', f.lower().replace('_', '-'))
    return re.sub(r"^([a-z0-9-]+)\.(png|jpg)$", r"\1", f)

def clean_icon_name(i):
    return re.sub(r"[^a-z0-9-]", "", i)

def generate_icon_list():
    dirs, files = staticfiles_storage.listdir(_icons_dir)
    names_clean = {}
    for f in files:
        # cleanup names by removing extension and converting to lowercase
        icon_name_clean = clean_filename(f)
        names_clean[icon_name_clean] = "%s/%s" % (_icons_dir, f)
    return names_clean

try:
    _icon_list = generate_icon_list()
except Exception as e:
    logger.warn(e)
    _icon_list = {}

def get_icon_list():
    return _icon_list.keys()

def icon_func(f):
    def return_value(icon_name):
        i = _icon_list.get(clean_icon_name(icon_name), None)
        if not i:
            return None
        return f(i)
    return return_value

get_icon_path = icon_func(staticfiles_storage.path)
get_icon_url = icon_func(staticfiles_storage.url)

def get_icon_url_dict():
    return {
        name: staticfiles_storage.url(path)
        for name, path in _icon_list.items()
    }

def get_hex_colour():
    rgb = [
        random.randint(0, 255),
        random.randint(80, 200),
        random.randint(200, 255)
    ]
    random.shuffle(rgb)
    return "#%02x%02x%02x" % tuple(rgb)