from django.contrib.gis.db import models
from django.contrib.postgres import fields as pg
from django.contrib.auth import models as auth_models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.files.images import get_image_dimensions
from django.core.exceptions import ValidationError, FieldDoesNotExist
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe

from colorfield.fields import ColorField
from datetime import datetime

import csv

from .icons import get_icon_list, get_hex_colour

class UserWithToken(auth_models.AbstractUser):
    """
    Custom user with attributes specific for map login and authentication
    """

    password = models.CharField(_('password'), max_length=128, blank=True, null=True)

    login_token = models.CharField(
        verbose_name = _("Login Token"),
        max_length = 256,
        blank = True,
        null = True,
        default = None,
        help_text = _("Enter a long, random string to enable passwordless login for this user. WARNING: Using the token, it is possible to get all permissions of this user, including the Admin Site!"),
    )

    class Meta:
        verbose_name = _('User')


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
    return { }

class BaseItemModel(models.Model):
    metadata    = models.JSONField(default=get_default_metadata, null=False, blank=True)
    updated     = models.DateTimeField(_('Last updated'), auto_now=True)
    created     = models.DateTimeField(_('When created'), auto_now_add=True)
    owner       = models.ForeignKey(UserWithToken, on_delete=models.SET_NULL, null=True, blank=True)
    
    @classmethod
    def get_default_pk(cls):
        return cls.default().pk

    def make_archive_entry(self):
        archive = self.metadata.get('archive', [])
        olddata = {
            'when': datetime.now().isoformat(),
            'on_model': {},
            'on_meta': {},
        }
        archive.append(olddata)
        # update in case it wasn't already there
        self.metadata['archive'] = archive

    def add_metadata(self, key, data=None, archive_entry=None):
        data = data or {}
        if key == 'archive':
            raise ValueError('cannot add archive data directly to model instance')
        elif key in self.metadata:
            archive_entry = archive_entry or self.make_archive_entry()
            archive_entry['on_meta'][key] = self.metadata.pop(key)
        self.metadata[key] = data
        return data, archive_entry

    def update_extra_fields(self, data, archive_entry=None):
        efs, archive_entry = self.add_metadata('extra_fields', archive_entry)
        for k, v in data.items():
            if k in efs:
                archive_entry = archive_entry or self.make_archive_entry()
                archive_entry['on_meta']['extra_fields'][k] = efs.pop(k)
            efs[k] = v
        return archive_entry

    def update_fields(self, data, archive_entry=None):
        """
        Update model fields from data (dict), recording history in metadata
        """
        for field_name, value in data.items():
            if field_name == 'metadata':
                archive_entry = self.update_extra_fields(value, archive_entry)
                continue
            
            if self._meta.get_field(field_name):
                old_val = getattr(self, field_name)
                if value != old_val:
                    setattr(self, field_name, value)
                    archive_entry = archive_entry or self.make_archive_entry()
                    archive_entry['on_model'][field_name] = old_val
        return archive_entry

    class Meta:
        abstract = True

class ImportDefinition(models.Model):
    name    = models.CharField(_('Name'), max_length=100)
    desc    = models.CharField(_('Description'), max_length=500)
    owner   = models.ForeignKey(
        UserWithToken,
        on_delete = models.SET_NULL,
        null = True,
        blank = True
    )

    mapping = models.JSONField(_('Field mapping data'), default=dict)

class Source(BaseItemModel):
    name        = pg.CICharField(max_length=100)
    description = models.TextField(blank=True)
    srcfile     = models.FileField(
        verbose_name = _('Spreadsheet source file'),
        upload_to = 'sources/',
        null = True,
        blank = True,
        help_text = _('Spreadsheet from which data was imported'),
    )

    can_update  = models.BooleanField(
        blank = True,
        null = False,
        default = True,
        help_text = _('If source can be updated by importing data')
    )
    pending_import = models.BooleanField(
        blank = True,
        null = False,
        default = True,
        help_text = _('If source data is awaiting import')
    )
    import_def  = models.ForeignKey(
        to = ImportDefinition,
        on_delete = models.SET_NULL,
        verbose_name = _('Import Definition'),
        blank = True,
        null = True,
        help_text = _('Import Definition which was used to import the data (ie. from a spreadsheet)')
    )
    
    @classmethod
    def default(cls):
        return cls.objects.get_or_create(name=_('(manually entered)'), can_update=False)[0]

    def __str__(self):
        return self.name if not self.description else "%s (%s)" % (self.name, self.description)

    class Meta:
        verbose_name = 'Data Source'


class BaseSourcedModel(BaseItemModel):
    # keep track of where the data came from, ie. for updating later from same source (eg. other databae, spreadsheet)
    source      = models.ForeignKey(Source, null=False, on_delete=models.CASCADE, default=Source.get_default_pk)
    # if the source has any unique numbers for each place (eg. geonoma feature_number)
    source_ref  = models.CharField(_('Source ref'), blank=True, null=True, max_length=50, help_text=_('Row ID/reference in source dataset'))
    
    class Meta:
        abstract = True

class Language(BaseSourcedModel):
    name        = pg.CICharField(max_length=100)
    alt_names   = pg.ArrayField(
                        pg.CICharField(max_length=100, blank=True),
                        verbose_name=_('List of alternative names'), blank=True, default=list)
    colour      = ColorField(default=get_hex_colour, help_text=_('Colour to display on map'))

    media       = GenericRelation('Media', related_query_name='language')
    objects     = PrefetchManager(select=['source'], prefetch=['media'])
    
    @classmethod
    def default(cls):
        return cls.objects.get_or_create(name=_('Unknown'))[0]
    
    def __str__(self):
        return self.name if not self.alt_names else "%s (%s)" % (self.name, ", ".join(self.alt_names))

# represents a physical location
class Place(BaseSourcedModel):
    category        = pg.CICharField(_('Type of place'), max_length=200, default='unknown')
    
    location        = models.GeometryField(
        verbose_name = _('Coordinates'),
        null = True,
        blank = True,
        spatial_index = True,
        geography = True,
        srid = 4326,
        help_text = mark_safe(_('WKT-formatted geography data. Eg: POINT (119.60872 -20.080861).' +
            '<a target="_blank" href="https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry">More info</a>'))
    )

    location_desc   = models.TextField(_('Description of location'), blank=True)
    desc            = models.TextField(_('Description'), blank=True)

    # whether the place information should be publicly visible
    is_public       = models.BooleanField(_('Is location public'), default=True)
    reviewed        = models.BooleanField(_('Has been reviewed'), blank=True, default=False)
    reviewer        = models.TextField(_('Reviewer'), blank=True, help_text=_('Name or contact of reviewer'), max_length=500)

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
        #(VIDEO, _('Video')),
        (OTHER, _('Other media')),
    ]
    
    file_type   = models.CharField(verbose_name=_('Type of media'), max_length=5, choices=MEDIA_TYPES)
    title       = models.CharField(verbose_name=_('Title'), max_length=200, blank=True)
    description = models.TextField(blank=True)
    file        = models.FileField(
        upload_to = '%Y/%m/%d/',
        max_length = 255,
        help_text = _('Note for images: resize large images (ie. more than 500x500 pixels) to improve loading speed')
    )
    
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

    def get_image_size(self):
        return get_image_dimensions(self.file.file)
