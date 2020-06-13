from django.contrib import admin
from .models import Language, Place, Word, Source

# Register your models here.

@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'category', 'location')
    list_filter = ('source', 'is_public', 'category', 'names__language')
    search_fields = ('names',)
    ordering = ('__str__', )

