from django.contrib.gis.db import models
from django.contrib.postgres import fields as pg
from django.contrib.auth import models as auth_models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

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

def get_default_metadata():
    return {}

class BaseItemModel(models.Model):
    metadata    = pg.JSONField(default=get_default_metadata, null=False, blank=True)
    updated     = models.DateTimeField('Last updated', auto_now=True)
    created     = models.DateTimeField('When created', auto_now_add=True)
    owner       = models.ForeignKey(auth_models.User, on_delete=models.SET_NULL, null=True)
    
    @classmethod
    def get_default_pk(cls):
        return cls.default().pk
    
    class Meta:
        abstract = True


class Source(BaseItemModel):
    name        = pg.CICharField(max_length=100)
    description = models.TextField(blank=True)
    srcfile     = models.FileField(upload_to='sources/', null=True, blank=True)
    
    @classmethod
    def default(cls):
        return cls.objects.get_or_create(name='Manual')[0]
    
    def __str__(self):
        return self.name if not self.description else "%s (%s)" % (self.name, self.description)


class BaseSourcedModel(BaseItemModel):
    # keep track of where the data came from, ie. for updating later from same source (eg. other databae, spreadsheet)
    source      = models.ForeignKey(Source, null=False, on_delete=models.CASCADE, default=Source.get_default_pk)
    # if the source has any unique numbers for each place (eg. geonoma feature_number)
    source_ref  = models.CharField('Source ref', blank=True, max_length=50, help_text='Row ID/reference in source dataset')
    
    class Meta:
        abstract = True


class Language(BaseSourcedModel):
    name        = pg.CICharField(max_length=100)
    url         = models.URLField('Glottolog URL', blank=True)
    alt_names   = pg.ArrayField(
                        pg.CICharField(max_length=100, blank=True),
                        verbose_name='List of alternative names', default=list)
    
    media       = GenericRelation('Media', related_query_name='language')
    objects     = PrefetchManager(prefetch=['media'])
    
    @classmethod
    def default(cls):
        return cls.objects.get_or_create(name='Unknown')[0]
    
    def __str__(self):
        return self.name if not self.alt_names else "%s (%s)" % (self.name, ", ".join(self.alt_names))

# represents a physical location
class Place(BaseSourcedModel):
    category        = pg.CICharField('Type of place', max_length=200, default='unknown')
    location        = models.GeometryField('Physical location', null=True, blank=True)
    location_desc   = models.TextField('Description of location', blank=True)
    desc            = models.TextField('Description', blank=True)

    # whether the place information should be publicly visible
    is_public       = models.BooleanField('Is location public', default=True)
    
    media   = GenericRelation('Media', related_query_name='place')
    objects = PrefetchManager(select=['source'], prefetch=['names', 'media'])

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
    name        = pg.CICharField('Name', max_length=200, blank=False)
    desc        = models.TextField('Meaning/description', blank=True)
    language    = models.ForeignKey(Language, null=False, on_delete=models.CASCADE, default=Language.get_default_pk)
    
    media   = GenericRelation('Media', related_query_name='word')
    objects = PrefetchManager(select=['language', 'source', 'place'], prefetch=['media'])
    
    def __str__(self):
        return ("[%s] %s" % (self.language.name, self.name)) + (": %s" % self.desc if self.desc else "")
    
    
class Media(BaseItemModel):
    IMAGE = 'IMG'
    AUDIO = 'AUD'
    VIDEO = 'VID'
    OTHER = 'OTH'
    
    MEDIA_TYPES = [
        (IMAGE, 'Image'),
        (AUDIO, 'Audio recording'),
        (VIDEO, 'Video'),
        (OTHER, 'Other media'),
    ]
    
    file_type   = models.CharField(verbose_name='Type of media', max_length=3, choices=MEDIA_TYPES)
    description = models.TextField(blank=True)
    file        = models.FileField(upload_to='media_uploads/', max_length=255)
    
    # use Django's contenttypes system to link a media to any other database item
    content_type    = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id       = models.PositiveIntegerField()
    linked_item     = GenericForeignKey('content_type', 'object_id')
    
    def __str__(self):
        return self.file.name
