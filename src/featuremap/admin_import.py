from django.contrib import admin, messages
from django import forms
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic.edit import FormView, CreateView, UpdateView
from django.utils.translation import gettext_lazy as _
from django.utils.html import mark_safe
from django.core.exceptions import ValidationError

import csv
import json
import logging

from featuremap.models import Place, Source
from .models import ImportDefinition
from .mappings import mappings
from .files import get_csv_info, import_csv_with_colmap

logger = logging.getLogger(__name__)

class AdminViewMixin:
    admin_site = None
    model = None
    title = ''

    def dispatch(self, request, *args, **kwargs):
        request.current_app = self.admin_site.name
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(self.admin_site.each_context(self.request))
        context['opts'] = self.model._meta
        context['title'] = self.title
        return context

def get_inverse_colmaps():
    inv_cols = {}
    misc_cols = {}
    for name, colmap in mappings.items():
        name = "py_%s" % name
        i, m = colmap.get_inv_colmap()
        inv_cols[name] = i
        misc_cols[name] = m
    return inv_cols, misc_cols

class PlaceImportUploadForm(forms.ModelForm):
    allowed_content_types = ['text']

    srcfile = forms.FileField(
        required = True,
        label = _('Upload a spreadsheet to import the data'),
        help_text = _("Only CSV files supported - open in Excel and 'Save As..' to .csv first if you have a different format"),
    )

    def clean_srcfile(self):
        """ checks the uploaded srcfile for consistency and updates the object metadata accordingly """
        srcfile = self.cleaned_data['srcfile']
        content_type = srcfile.content_type.split('/')[0]
        if not content_type in self.allowed_content_types:
            raise ValidationError(_("Only CSV file imports are supported, please check that the format is correct (.csv) and try again."))
        
        try:
            src_fields, num_rows, num_weird_rows = get_csv_info(srcfile)
            self.csv_metadata = {
                'filename_orig': srcfile.name,
                'src_fields': src_fields,
                'num_rows': num_rows,
                'num_weird_rows': num_weird_rows,
            }
            logger.debug(self.csv_metadata)
        except (csv.Error, TypeError, ValueError) as e:
            logger.error(str(e))
            raise ValidationError(_("Could not parse CSV data, try exporting again using a different program."))
        except Exception as e:
            #raise e
            logger.error(str(e))
            raise ValidationError(_("A server error occurred, unable to handle uploaded file."))
        return srcfile

    def save(self, commit=True):
        obj = super().save(commit=False)
        # set some values on the new Source object
        obj.can_update = True
        obj.pending_import = True
        obj.import_def = None
        if not obj.description:
            obj.description = _("Imported from '%s'") % obj.srcfile.name

        obj.add_metadata('import_csv_upload', self.csv_metadata)
        obj.save()
        return obj

    class Meta:
        model = Source
        fields = ['name', 'srcfile', 'description']
        widgets = {
            'description': forms.TextInput,
        }

def get_sources():
    return Source.objects.filter(
        can_update__exact = True,
        metadata__import_csv_upload__isnull=False,
    )

def get_source_choices():
    srcs = [
        (s.id, str(s)) for s in get_sources()
    ] + [ (None, 'None (import as new source)') ]
    return srcs

def get_mapping_choices():
    try:
        in_db = ImportDefinition.objects.all()
        choices = [
            ("py_%s" % k, k) for k in mappings.keys()
        ]
        for idef in in_db:
            choices.append((idef.id, idef.name))
    except Exception:
        return []
    return choices

class PlaceImportConfigForm(forms.ModelForm):
    # Field Definitions #
    map_base = forms.ChoiceField(
        label = _('Base field mapping'),
        required = True,
        choices = get_mapping_choices,
    )

    source = forms.ChoiceField(
        label = _('Existing source to update'),
        required = False,
        choices = get_source_choices,
    )

    def clean(self):
        data = super().clean()
        return data

    def get_mapping(self):
        m = self.cleaned_data['map_base']
        if m[:3] != 'py_':
            raise NotImplementedError("Only manually coded field mappings are supported")
        return mappings[m[3:]]

    def save(self):
        """ Save the Source object and import data """
        source = super().save()
        colmap = self.get_mapping()
        try:
            num_rows, new, updated = import_csv_with_colmap(source.srcfile, colmap, source)
        except Exception as e:
            logger.error("csv import error: %s" % e)
            raise ValidationError(_('Errors occurred when importing the CSV file, check the options are correct and try again.'))
        
        models = set(list(new.keys()) + list(updated.keys()))

        self.import_str = ", ".join([
            _('%s (%d new / %d updated)') % (
                name,
                new[name] if name in new else 0,
                updated[name] if name in updated else 0
            ) for name in models
        ])

        source.pending_import = False
        source.save()
        return source

    class Meta:
        model = Source
        fields = []

class PlaceImportUploadView(AdminViewMixin, CreateView):
    template_name = 'admin/import/upload.html'
    form_class = PlaceImportUploadForm
    model = Source
    pk_url_kwarg = 'source_id'
    title = _('Upload CSV')

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx.update({
            'submit_text': _('Next'),
        })
        return ctx

    def get_success_url(self):
        return reverse('admin:place_import_config', kwargs={'source_id': self.object.pk })

class PlaceImportConfigView(AdminViewMixin, UpdateView):
    template_name = 'admin/import/config.html'
    form_class = PlaceImportConfigForm
    model = Source
    pk_url_kwarg = 'source_id'
    title = _('Import CSV')

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(can_update__exact=True, srcfile__isnull=False)

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        inv_cols, misc_cols = get_inverse_colmaps()
        csv_metadata = self.object.metadata.get('import_csv_upload', None)
        logger.debug('csv import metadata for Source id=%s: %s' % (self.object.pk, csv_metadata))
        ctx.update({
            'submit_text': _('Confirm Import'),
            'csv_fields': csv_metadata,
            'inv_colmaps': inv_cols,
            'misc_cols': misc_cols,
            'js': {
                'inv_colmaps': inv_cols,
                'misc_cols': misc_cols,
                'csv_fields': csv_metadata,
            },
        })
        return ctx

    def post(self, request, *args, **kwargs):
        """ override ProcessFormView's default behaviour to allow handle ValidationErrors generated in form.save() """
        self.object = self.get_object()
        form = self.get_form()
        if not form.is_valid():
            return self.form_invalid(form)

        try:
            self.object = form.save()
            messages.add_message(request, messages.INFO, _('Successfully imported: %s') % form.import_str)
            return HttpResponseRedirect(self.get_success_url())
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('admin:featuremap_place_changelist', current_app=self.admin_site.name)
        #return reverse('admin:place_import_confirm', kwargs={'source_id': self.get_object().pk })
    
class PlaceImportConfirmView(FormView, AdminViewMixin):
    template_name = 'admin/import/confirm.html'
    model = Source
    pk_url_kwarg = 'source_id'
    
    def get_success_url(self):
        return reverse('admin:featuremap_place_changelist', current_app=self.admin_site.name)

