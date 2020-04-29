from django.contrib import admin
from .models import Language, Place

# Register your models here.
@admin.register(Language)
class LangAdmin(admin.ModelAdmin):
    pass

@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    pass
