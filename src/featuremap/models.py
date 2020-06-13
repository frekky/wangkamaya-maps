from django.contrib.gis.db import models
from django.contrib.postgres import fields as postgres_fields
from django.contrib.auth import models as auth_models

def default_metadata():
    return {}

class BaseItemModel(models.Model):
    metadata    = postgres_fields.JSONField(default=default_metadata)
    updated     = models.DateTimeField('Last updated', auto_now=True)
    created     = models.DateTimeField('When created', auto_now_add=True)
    owner       = models.ForeignKey(auth_models.User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        abstract = True

class Language(BaseItemModel):
    name        = models.CharField(max_length=100)
    url         = models.URLField('Glottolog URL', blank=True)
    alt_names   = models.ManyToManyField('Word', verbose_name='Other names', related_name='+')
 
class Source(BaseItemModel):
    name        = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    srcfile     = models.FileField(upload_to='sources/', null=True, blank=True)

class BaseSourcedModel(BaseItemModel):
    # keep track of where the data came from, ie. for updating later from same source (eg. other databae, spreadsheet)
    source      = models.ForeignKey(Source, null=False, on_delete=models.PROTECT)
    # if the source has any unique numbers for each place (eg. geonoma feature_number)
    source_ref   = models.CharField('Source ref', max_length=50, help_text='Row ID/reference in source dataset')
    
    class Meta:
        abstract = True
        
class PrefetchManager(models.Manager):
    def __init__(self, prefetch=None, select=None, *args, **kwargs):
        self.prefetch = prefetch
        self.select = select
        super().__init__(*args, **kwargs)
    
    def get_queryset(self):
        qs = super().get_queryset()
        if self.select:
            qs = qs.select_related(*self.select)
        if self.prefetch:
            qs = qs.prefetch_related(*self.prefetch)
        return qs
    
class Word(BaseSourcedModel):
    lexeme      = models.CharField('Lexeme', max_length=200, blank=False)
    language    = models.ForeignKey(Language, null=False, on_delete=models.PROTECT)
    recording   = models.FileField('Recording', upload_to='recordings/', null=True, blank=True)
    metadata    = postgres_fields.JSONField('Metadata', blank=False)
    
    objects = PrefetchManager(select=['langauge', 'source'])

# represents a physical location
class Place(BaseSourcedModel):
    names       = models.ManyToManyField(Word)
    category    = models.CharField('Type of place', max_length=200, default='unknown')
    location    = models.GeometryField('Physical location', null=True, blank=True)
    location_desc = models.CharField('Description of location', max_length=500, blank=True)
    desc        = models.CharField('Description', max_length=500)

    # whether the place information should be publicly visible
    is_public   = models.BooleanField('Is location public', default=True)
    
    objects = PrefetchManager(select=['source'], prefetch=['names'])

    def __str__(self):
        s = ""
        for n in self.names.all():
            if s:
                s += ", "
            s += '%s (%s)' % (n.lexeme, n.language.name)
        return s
