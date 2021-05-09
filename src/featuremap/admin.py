from django.contrib import admin
from django.contrib.gis.db import models
from django.contrib.gis.forms.widgets import OSMWidget
from django.forms import widgets
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group

from admin_action_buttons.admin import ActionButtonsMixin as ABM

from .admin_site import admin_site
from .models import Language, Place, Word, Source, Media
from .auth import UserWithToken, UserWithTokenAdmin

admin_site.register(UserWithToken, UserWithTokenAdmin)
#admin_site.register(Group, GroupAdmin)

class MyAdminMixin:
    formfield_overrides = {
        models.GeometryField: {
            'widget': widgets.TextInput(attrs={'class': 'vTextField'}),
        },
        models.TextField: {
            'widget': widgets.Textarea(attrs={'rows': '1'}),
        },
        models.JSONField: {
            'widget': widgets.Textarea(attrs={'rows': '1'}),
        }
    }

class MyOSMWidget(OSMWidget):
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

#@admin.register(Media, site=admin_site)
class MediaAdmin(admin.ModelAdmin):
    pass

class MediaInline(MyAdminMixin, GenericTabularInline):
    extra = 0
    model = Media
    readonly_fields = ('created', 'updated')

    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'file_type', 'file')
        }),
        #(_('Advanced'), {
        #    'classes': ('collapse', ),
        #    'fields': ('metadata', 'owner')
        #}),
    )


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

class PlaceNameInline(admin.TabularInline):
    fields = ['name', 'desc', 'language']
    extra = 0
    model = Word

    formfield_overrides = {
        models.TextField: {
            'widget': widgets.TextInput,
        }
    }

@admin.register(Place, site=admin_site)
class PlaceAdmin(MyAdminMixin, ABM, admin.ModelAdmin):
    list_display = ('__str__', 'category', 'location', 'icon')
    list_filter = (LocationListFilter, 'is_public', 'source', 'category', 'icon')
    list_per_page = 1000
    list_select_related = True
    search_fields = ('names__name', 'desc', 'category', 'location_desc', )

    fieldsets = (
        (None, {
            'fields': ('category', 'desc', 'location', 'location_desc', 'icon', 'is_public', 'reviewed')
        }),
        (_('Advanced'), {
            'classes': ('collapse', ),
            'fields': ('reviewer', 'source', 'source_ref', 'metadata')
        })
    )
    inlines = [
        PlaceNameInline,
        MediaInline,
    ]


@admin.register(Source, site=admin_site)
class SourceAdmin(MyAdminMixin, ABM, admin.ModelAdmin):
    list_display = ('name', 'description', 'srcfile', 'updated')
    search_fields = ('name', 'metadata', 'description')
    ordering = ('created', )

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'srcfile',)
        }),
        (_('Advanced'), {
            'classes': ('collapse', ),
            'fields': ('owner', 'pending_import', 'can_update', 'metadata', )
        }),
    )

@admin.register(Language, site=admin_site)
class LangAdmin(MyAdminMixin, ABM, admin.ModelAdmin):

    def lang_colour(self, lang):
        html = render_to_string('widgets/colour_circle.html', {'colour': lang.colour})
        return mark_safe(html)
    lang_colour.short_description = 'Map icon colour'
    lang_colour.allow_tags = True

    list_display = ('name', 'lang_colour', 'alt_names', )
    inlines = [
        MediaInline,
    ]
    fields = ('name', 'alt_names', 'colour', )

