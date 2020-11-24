from django.contrib.gis.db import models
from django.contrib.postgres import fields as pg
from django.contrib.auth import models as auth_models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from colorfield.fields import ColorField

from .icons import get_icon_list

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
    updated     = models.DateTimeField(_('Last updated'), auto_now=True)
    created     = models.DateTimeField(_('When created'), auto_now_add=True)
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
        return cls.objects.get_or_create(name=_('Manual'))[0]
    
    def __str__(self):
        return self.name if not self.description else "%s (%s)" % (self.name, self.description)


class BaseSourcedModel(BaseItemModel):
    # keep track of where the data came from, ie. for updating later from same source (eg. other databae, spreadsheet)
    source      = models.ForeignKey(Source, null=False, on_delete=models.CASCADE, default=Source.get_default_pk)
    # if the source has any unique numbers for each place (eg. geonoma feature_number)
    source_ref  = models.CharField(_('Source ref'), blank=True, max_length=50, help_text=_('Row ID/reference in source dataset'))
    
    class Meta:
        abstract = True


class Language(BaseSourcedModel):
    name        = pg.CICharField(max_length=100)
    url         = models.URLField(_('Glottolog URL'), blank=True)
    alt_names   = pg.ArrayField(
                        pg.CICharField(max_length=100, blank=True),
                        verbose_name=_('List of alternative names'), default=list)
    colour      = ColorField(default='#f0e800', help_text=_('Colour to display on map'))

    media       = GenericRelation('Media', related_query_name='language')
    objects     = PrefetchManager(select=['source'], prefetch=['media'])
    
    @classmethod
    def default(cls):
        return cls.objects.get_or_create(name='Unknown')[0]
    
    def __str__(self):
        return self.name if not self.alt_names else "%s (%s)" % (self.name, ", ".join(self.alt_names))

# represents a physical location
class Place(BaseSourcedModel):
    category        = pg.CICharField(_('Type of place'), max_length=200, default='unknown')
    location        = models.GeometryField(_('Physical location'), null=True, blank=True,
                           spatial_index=True, geography=True, srid=4326)
    location_desc   = models.TextField(_('Description of location'), blank=True)
    desc            = models.TextField(_('Description'), blank=True)

    # whether the place information should be publicly visible
    is_public       = models.BooleanField(_('Is location public'), default=True)

    icon            = models.CharField(_('Map icon'), max_length=100, default='place-name',
                            choices=[(n, n) for n in get_icon_list()])
    
    media   = GenericRelation('Media', related_query_name='place')
    objects = PrefetchManager(select=['source'], prefetch=['names', 'names__media', 'names__source', 'names__language', 'media'])

    def __str__(self):
        try:
            names = self.names.all()
        except Exception:
            return _("(unknown name)")
        s = ""
        for n in names:
            if s:
                s += ", "
            s += '%s (%s)' % (n.name, n.language.name)
        return s

    
class Word(BaseSourcedModel):
    class Meta:
        verbose_name = _('Place Name')
        verbose_name_plural = _('Place Names')
    
    place       = models.ForeignKey(Place, related_name='names', on_delete=models.SET_NULL, null=True)
    name        = pg.CICharField(_('Name'), max_length=200, blank=False)
    desc        = models.TextField(_('Meaning/description'), blank=True)
    language    = models.ForeignKey(Language, null=False, on_delete=models.CASCADE, default=Language.get_default_pk)
    
    media   = GenericRelation('Media', related_query_name='word')
    objects = PrefetchManager(select=['language', 'source', 'place'], prefetch=['media'])
    
    def __str__(self):
        return ("[%s] %s" % (self.language.name, self.name)) + (": %s" % self.desc if self.desc else "")
    
    
class Media(BaseItemModel):
    class Meta:
        verbose_name = _('Media object')
        
    IMAGE = 'image'
    AUDIO = 'audio'
    VIDEO = 'video'
    OTHER = 'other'
    
    MEDIA_TYPES = [
        (IMAGE, _('Image')),
        (AUDIO, _('Audio recording')),
        (VIDEO, _('Video')),
        (OTHER, _('Other media')),
    ]
    
    file_type   = models.CharField(verbose_name=_('Type of media'), max_length=5, choices=MEDIA_TYPES)
    title       = models.CharField(verbose_name=_('Title'), max_length=200, blank=True)
    description = models.TextField(blank=True)
    file        = models.FileField(upload_to='%Y/%m/%d/', max_length=255)
    
    # use Django's contenttypes system to link a media to any other database item
    content_type    = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id       = models.PositiveIntegerField()
    linked_item     = GenericForeignKey('content_type', 'object_id')
    
    def __str__(self):
        return self.file.name
    
    def get_absolute_url(self):
        return self.file.url
    
    def get_template(self):
        return 'media/' + self.file_type + '.html'
    
    def get_css_class(self):
        return self.file_type
    
