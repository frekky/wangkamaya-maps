from django.contrib import admin
from .models import Place

# Register your models here.

@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'place_type', 'desc', 'lang', 'location')
    list_filter = ('source', 'is_public', 'lang', 'place_type')
    search_fields = ('name', 'name_eng')
    ordering = ('name', )
