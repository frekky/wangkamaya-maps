from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, HttpResponseForbidden
from django.conf import settings
from django.views.generic.base import TemplateView
from django.views.decorators.gzip import gzip_page
from django.utils.translation import gettext as _
from django.forms.models import model_to_dict
from django.contrib.gis import geos
from django.contrib.auth.decorators import login_required
from django.contrib import auth
from django.urls import reverse, get_script_prefix

import geojson
import json

from django.core.serializers import serialize
from .models import Place, Language, UserWithToken
from .icons import get_icon_url_dict
from .auth import login_or_token_required
from .apps import get_site_name, get_detail_url

import logging
logger = logging.getLogger(__name__)

class AboutView(TemplateView):
    template_name='info_about.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['app_version'] = getattr(settings, 'SITE_VERSION', _('(not set)'))
        ctx['title'] = get_site_name()
        return ctx

def get_js_context():
    """
    Returns a dict to be translated into javascript variables in the rendered view DOM.
    See templates/json_data.html
    """
    return {
        'data_url': reverse('featuremap:data'),
        'detail_url_base': get_script_prefix() + get_detail_url(),
        'map_url': reverse('featuremap:map'),
        'about_url': reverse('featuremap:about'),
        'csrf_cookie_name': getattr(settings, 'CSRF_COOKIE_NAME'),
    }

def get_map_context(request, *args, **kwargs):
    return {
        'title': get_site_name(),
        'js': get_js_context(),
        'langs': Language.objects.all(),
    }

@login_required
def leaflet_view(request, *args, **kwargs):
    """ The main maps view """
    return render(request, 'maps_leaflet.html', get_map_context(request, *args, **kwargs))

def place_detail(request, *args, place_id=None, **kwargs):
    """ The place detail view """
    context = {
        'item': Place.objects.get(id=place_id),
    }
    return render(request, 'place_detail.html', context)

def _get_basic_data(inst, extrafields=[]):
    """ gets the baseline data in a dict form """
    fields = ['id', 'updated', 'created', 'owner', 'metadata']
    data = model_to_dict(inst, fields = fields + extrafields)
    data['media'] = [
        {
            "id": m.pk,
            "href": m.get_absolute_url(),
            "type": m.file_type,
            "desc": m.description,
        }
        for m in inst.media.all()
    ]
    data['source'] = inst.source.id if inst.source else None
    return data

def _get_word(w):
    data = _get_basic_data(w)
    data.update({
        "name": w.name,
        "desc": w.desc,
        "lang": {
            "id": w.language.pk,
            "name": w.language.name,
            "colour": w.language.colour,
        },
    })
    return data
    
def _get_place_properties(p):
    # transform DB geometries into workable format
    #p.location.coords = p.location.coords[::-1]
    props = _get_basic_data(p, ['category', 'icon'])
    props.update({
        "names": [_get_word(w) for w in p.names.all()],
    })
    return props

def _get_place(p):
    geom = geojson.loads(p.location.geojson);
    props = _get_place_properties(p)
    return geojson.Feature(geometry=geom, properties=props)

@login_required
@gzip_page
def places_json(request):
    """ basically just dump the database into JSON, with some optimisations for the map service """
    places = Place.objects.filter(location__isnull=False)

    if not request.user.is_authenticated:
        places = places.filter(is_public=True)

    if request.method == 'POST':
        # parse json request data and include in query
        try:
            data = json.loads(request.body)
            b = data.get('bounds', None)
            if b:
                bbox = geos.Polygon.from_bbox((b['sw']['lng'], b['sw']['lat'],
                                               b['ne']['lng'], b['ne']['lat']))
                logger.debug('search bbox=%s' % bbox)
                places = places.filter(location__bboverlaps=bbox)

            loaded_ids = data.get('alreadyLoaded', None)
            if loaded_ids and isinstance(loaded_ids, list):
                 places = places.exclude(id__in=loaded_ids)
        except (json.JSONDecodeError, KeyError):
            logger.error('invalid request data')
            return HttpResponseBadRequest()

    # make a feature collection for json export
    features = geojson.FeatureCollection([_get_place(p) for p in places])
    
    # include some data for languages etc. in the response
    langs = []
    for p in places:
        for w in p.names.all():
            if not w.language in langs:
                langs.append(w.language)
            
    langs.sort(key = lambda l: l.name)
                
    features.metadata = {
        "langs": [model_to_dict(l) for l in langs],
        "icons": get_icon_url_dict(),
    }
    
    features_json = geojson.dumps(features)
    return HttpResponse(features_json, content_type='application/json; charset=utf-8')