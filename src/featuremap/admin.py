from django.contrib import admin
from django.contrib.gis.db import models
from django.contrib.gis.forms import widgets
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.admin import GenericTabularInline
from admin_action_buttons.admin import ActionButtonsMixin as ABM
from .models import Language, Place, Word, Source, Media
    
    
class MyOSMWidget(widgets.OSMWidget):
    """
    An OpenLayers/OpenStreetMap-based widget. Fixed to work with WGS84 coordinates
    """
    def serialize(self, value):
        return value.json if value else ''

    def deserialize(self, value):
        geom = super().deserialize(value)
        # GeoJSON assumes WGS84 (4326). Use the map's SRID instead.
        if geom.srid != 4326:
            geom.transform(4326)
        return geom

@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    pass

class MediaInline(GenericTabularInline):
    extra = 0
    model = Media

class LocationListFilter(admin.SimpleListFilter):
    title = _('location')
    parameter_name = 'location'
    
    def lookups(self, request, model_admin):
        return (
            ('nonnull', _('With coordinates')),
            ('null', _('No location')),
        )
        
    def queryset(self, request, queryset):
        if self.value() == 'null':
            return queryset.filter(location__isnull=True)
        elif self.value() == 'nonnull':
            return queryset.filter(location__isnull=False)

@admin.register(Word)
class WordAdmin(ABM, admin.ModelAdmin):
    list_display = ('name', 'place', 'language', 'desc')
    list_filter = ('language', )
    search_fields = ('name', 'desc')
    inlines = [
        MediaInline,
    ]

class PlaceNameInline(admin.TabularInline):
    fields = ['name', 'desc', 'language']
    extra = 0
    model = Word

@admin.register(Place)
class PlaceAdmin(ABM, admin.ModelAdmin):
    list_display = ('__str__', 'category', 'location')
    list_filter = (LocationListFilter, 'is_public', 'source', 'category')
    search_fields = ('location_desc', )
    fieldsets = (
        (None, {
            'fields': ('category', 'desc', 'location', 'location_desc', )
        }),
        (_('Advanced'), {
            'classes': ('collapse', ),
            'fields': ('is_public', 'source', 'source_ref', 'metadata')
        })
    )
    inlines = [
        PlaceNameInline,
        MediaInline,
    ]
    formfield_overrides = {
        models.GeometryField: {
            'widget': MyOSMWidget(attrs={
                'default_lon': 118.648,
                'default_lat': -20.384,
                'default_zoom': 8,
                'display_raw': True,
            })
        },
    }
    
@admin.register(Source)
class SourceAdmin(ABM, admin.ModelAdmin):
    list_display = ('name', 'description', 'srcfile', 'updated')
    search_fields = ('name', 'metadata', 'description')
    ordering = ('created', )
    inlines = [
        MediaInline,
    ]

@admin.register(Language)
class LangAdmin(ABM, admin.ModelAdmin):
    list_display = ('name', 'alt_names', 'url')
    inlines = [
        MediaInline,
    ]

