from django.contrib.gis.db import models
from django.contrib.postgres import fields as postgres_fields
from django.contrib.auth import models as auth_models

def default_metadata():
    return {}

class BaseItemModel(models.Model):
    metadata    = postgres_fields.JSONField(default=default_metadata, null=False, blank=True)
    updated     = models.DateTimeField('Last updated', auto_now=True)
    created     = models.DateTimeField('When created', auto_now_add=True)
    owner       = models.ForeignKey(auth_models.User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        abstract = True

class Language(BaseItemModel):
    name        = models.CharField(max_length=100)
    url         = models.URLField('Glottolog URL', blank=True)
    alt_names   = models.CharField('Alternative names', max_length=500, blank=True)
    
    def __str__(self):
        return self.name if not self.alt_names else "%s (also %s)" % (self.name, self.alt_names)
 
class Source(BaseItemModel):
    name        = models.CharField(max_length=100)
    description = models.CharField(max_length=200, blank=True)
    srcfile     = models.FileField(upload_to='sources/', null=True, blank=True)
    
    @classmethod
    def default(cls):
        return cls.objects.get_or_create(name__iexact='manual')[0]
    
    def __str__(self):
        return self.name if not self.description else "%s (%s)" % (self.name, self.description)

class BaseSourcedModel(BaseItemModel):
    # keep track of where the data came from, ie. for updating later from same source (eg. other databae, spreadsheet)
    source      = models.ForeignKey(Source, null=False, on_delete=models.PROTECT, default=Source.default)
    # if the source has any unique numbers for each place (eg. geonoma feature_number)
    source_ref   = models.CharField('Source ref', blank=True, max_length=50, help_text='Row ID/reference in source dataset')
    
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

# represents a physical location
class Place(BaseSourcedModel):
    category    = models.CharField('Type of place', max_length=200, default='unknown')
    location    = models.GeometryField('Physical location', null=True, blank=True)
    location_desc = models.CharField('Description of location', max_length=500, blank=True)
    desc        = models.CharField('Description', max_length=2000, blank=True)

    # whether the place information should be publicly visible
    is_public   = models.BooleanField('Is location public', default=True)
    
    objects = PrefetchManager(select=['source'], prefetch=['names'])

    def __str__(self):
        try:
            names = self.names.all()
        except Exception:
            return "(unknown name)"
        s = ""
        for n in names:
            if s:
                s += ", "
            s += '%s (%s)' % (n.name, n.language.name)
        return s

    
class Word(BaseSourcedModel):
    class Meta:
        verbose_name = 'Place Name'
        verbose_name_plural = 'Place Names'
    
    place       = models.ForeignKey(Place, related_name='names', on_delete=models.SET_NULL, null=True)
    name        = models.CharField('Name', max_length=200, blank=False)
    desc        = models.CharField('Meaning/description', max_length=2000, blank=True)
    language    = models.ForeignKey(Language, null=False, on_delete=models.PROTECT)
    recording   = models.FileField('Recording', upload_to='recordings/', null=True, blank=True)
    
    objects = PrefetchManager(select=['language', 'source', 'place'])
