from django.shortcuts import render
from django.http import HttpResponse

from django.core.serializers import serialize
from .models import Place


# Create your views here.
def list_places(request, *args, **kwargs):
    return render(request, 'list_places.html', {'places': Place.objects.filter(is_public=True)})

def map_view(request, *args, **kwargs):
    rows_lang = Place.objects.filter(is_public=True, location__isnull=False).distinct('lang').values('lang')
    langs = []
    for l in rows_lang:
        if l['lang'] != '':
            langs += [l['lang']]
        else:
            langs += ['Unknown']

    context = {
        'langs': langs,
    }

    return render(request, 'map.html', context)

def places_json(request, *args, **kwargs):
    json = serialize('geojson',
                     Place.objects.filter(is_public=True, location__isnull=False),
                     geometry_field='location',
                     fields=('name', 'name_eng', 'place_type', 'desc', 'lang', 'source')
                )
    #return HttpResponse("jsonp_callback(JSON.parse('%s'))" % json, content_type='application/javascript')
    return HttpResponse(json, content_type='text/javascript')
