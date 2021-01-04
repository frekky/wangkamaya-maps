from django.urls import path, register_converter, reverse_lazy
from django.views.generic.base import RedirectView
from django.contrib.auth import views as auth_views

from featuremap import views
from featuremap.admin import admin_site

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
    path('', RedirectView.as_view(url=reverse_lazy('featuremap:map'), permanent=True)),
    path('list/', views.list_places, name='list'),
    path('map/', views.leaflet_view, name='map'),
    path('data/', views.places_json, name='data'),
    path('info/<int:place_id>/', views.place_detail, name='detail'),
    path('data/<point:bbox_sw>/<point:bbox_ne>/', views.places_json, name='databbox'),
    path('about/', views.AboutView.as_view(), name='about'),

    # TODO: email configuration
    #path('admin/password_reset/', auth_views.PasswordResetView.as_view(), name='admin_password_reset'),
    #path('admin/password_reset/done', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    #path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    #path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('admin/', admin_site.urls),
]
