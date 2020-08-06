from django.contrib import admin
from django.contrib.gis.db import models
from django.contrib.gis.forms import widgets
from .models import Language, Place, Word, Source

@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ('name', 'place', 'language', 'desc')
    list_filter = ('language', )
    search_fields = ('name', 'desc')

class PlaceNameInline(admin.TabularInline):
    fields = ['name', 'desc', 'language', 'recording']
    extra = 1
    model = Word

@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'category', 'location')
    list_filter = ('source', 'is_public', 'category')
    search_fields = ('location_desc', )
    fields = ['category', 'desc', 'location_desc', 'location', 'is_public', 'source', 'source_ref', 'metadata']
    #ordering = ('__str__', )
    inlines = [
        PlaceNameInline,
    ]
    formfield_overrides = {
        models.GeometryField: {'widget': widgets.OSMWidget(attrs={'default_lon': 118.648, 'default_lat': -20.384, 'default_zoom': 8}) },
    }
    
@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'srcfile', 'updated')
    search_fields = ('name', 'metadata', 'description')
    ordering = ('created', )

@admin.register(Language)
class LangAdmin(admin.ModelAdmin):
    list_display = ('name', 'alt_names', 'url')
