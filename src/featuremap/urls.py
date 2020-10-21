from django.urls import path, register_converter
from featuremap import views

class PointConverter:
    regex = '-*[0-9]{1,3}\.*[0-9]{0,10},-*[0-9]{1,3}\.*[0-9]{0,10}'
    
    def to_python(self, value):
        try:
            x, y = [float(s) for s in value.split(",")]
            return x, y
        except:
            raise ValueError()
        
    def to_url(self, value):
        return '%.10f,%.10f' % (value[0], value[1])

app_name = 'featuremap'

register_converter(PointConverter, 'point')

urlpatterns = [
    path('list/', views.list_places, name='list'),
    path('map/', views.map_view, name='map'),
    path('leaflet/', views.leaflet_view, name='lmap'),
    path('map_inline/', views.basic_map_view, name='map_inline'),
    path('data/', views.places_json, name='data'),
    path('data/<point:bbox_sw>/<point:bbox_ne>/', views.places_json, name='databbox'),
]
