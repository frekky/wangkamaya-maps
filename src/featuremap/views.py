from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.gzip import gzip_page
from django.utils.translation import gettext as _
from django.forms.models import model_to_dict
from django.contrib.gis import geos

import geojson

from django.core.serializers import serialize
from .models import Place, Language

import logging
logger = logging.getLogger(__name__)

# Create your views here.
def list_places(request, *args, **kwargs):
    return render(request, 'list_places.html', {'places': Place.objects.filter(is_public=True)})

def get_map_context(request, *args, **kwargs):
    return {
        'title': _('Maps'),
        'langs': Language.objects.all(),
        'gmaps_apikey': getattr(settings, 'GMAPS_API_KEY', ''),
    }

def map_view(request, *args, **kwargs):
    context = get_map_context(request, *args, **kwargs)
    return render(request, 'map_basic.html', context)

def leaflet_view(request, *args, **kwargs):
    context = {
        'title': _('Map page'),
        'langs': Language.objects.all(),
    }
    return render(request, 'leaflet_basic.html', context)

def basic_map_view(request, *args, **kwargs):
    return render(request, 'map_basic.html', get_map_context(request, *args, **kwargs))

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
        "lang": (w.language.pk, w.language.name),
    })
    return data
    
def _get_place(p):
    # transform DB geometries into workable format
    #p.location.coords = p.location.coords[::-1]
    geom = geojson.loads(p.location.geojson);
    props = _get_basic_data(p, ['category'])
    props.update({
        "names": [_get_word(w) for w in p.names.all()],
        
    })
    return geojson.Feature(geometry=geom, properties=props)
    
@gzip_page
def places_json(request, *args, bbox_sw=None, bbox_ne=None, **kwargs):
    """ simple view to dump the contents of the database into JSON """
    places = Place.objects.filter(is_public=True, location__isnull=False)

    if not (bbox_sw is None or bbox_ne is None):
        logger.debug("bbox_sw=%s bbox_ne=%s" % (bbox_sw, bbox_ne))
        bbox = geos.Polygon.from_bbox((bbox_sw[0], bbox_sw[1], bbox_ne[0], bbox_ne[1]))
        places = places.filter(location__bboverlaps=bbox)
        logger.debug("search bbox=%s" % bbox)
    
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
        #"bounds": places.aggregate(Extent('location')),
    }
    
    json = geojson.dumps(features)
    return HttpResponse(json, content_type='application/json; charset=utf-8')

def save_json(request, *args, **kwargs):
    """ possible feature: save changes made in web interface into database """
    pass
