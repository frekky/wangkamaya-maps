from django.contrib import admin
from django.contrib.gis.db import models
from featuremap.models import Language, Place, Word, Source


def clear_source(modeladmin, request, queryset):
    """ delete a Source and its associated objects from the database """
    pass