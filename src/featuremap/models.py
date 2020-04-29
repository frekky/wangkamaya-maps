from django.contrib.gis.db import models
from django.contrib.postgres import fields as postgres_fields
#from django.db import models

class Language(models.Model):
    name    = models.CharField('Language name', max_length=200)
    region  = models.GeometryField('Approximate language distribution region(s)')


# represents a physical location
class Place(models.Model):
    name        = models.CharField('Name', max_length=200, blank=True)
    name_eng    = models.CharField('English name', max_length=200, blank=True)
    place_type  = models.CharField('Type of place', max_length=200, default='unknown')
    location    = models.GeometryField('Physical location')
    location_desc = models.CharField('Description of location', max_length=500, blank=True)
    desc        = models.CharField('Description', max_length=500)
    lang        = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True, blank=True, related_name='places')

    # keep track of where the data came from, ie. for updating later from same source (eg. other databae, spreadsheet)
    source      = models.CharField('Data source', max_length=200, blank=False, default='unknown')
    # if the source has any unique numbers for each place (eg. geonoma feature_number)
    source_id   = models.CharField('Data source feature id', max_length=20, blank=True)

    # whether the place information should be publicly visible
    is_public   = models.BooleanField('Is location public', default=True)

    # for places which are part of a sequence (Brandenstein, 1973), or inherently linked to some specific location
    parent      = models.ForeignKey("Place", on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    # any additional data is stored as variable length JSON
    data        = postgres_fields.JSONField('Additional data', blank=True)

    date_added  = models.DateTimeField(auto_now_add=True)
    date_changed = models.DateTimeField(auto_now=True)

    def __str__(self):
        s = ""
        if self.name:
            s = name
            if self.name_eng:
                s += " (" + self.name_eng + ")"
        elif self.name_eng:
            s = self.name_eng
        else:
            s = "(no name)"
        return s
