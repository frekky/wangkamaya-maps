from django.contrib import admin
from .models import Language, Place

# Register your models here.
@admin.register(Language)
class LangAdmin(admin.ModelAdmin):
    pass

@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'place_type', 'desc', 'lang')
    list_filter = ('source', 'is_public', 'lang', 'place_type')
