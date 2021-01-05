from django.contrib import admin
from django import forms
from django.urls import reverse
from django.views.generic.edit import FormView
from django.utils.translation import gettext_lazy as _
from django.utils.html import mark_safe
import json

from featuremap.models import Place, Source
from .models import ImportDefinition
from .mappings import mappings

class AdminViewMixin:
    admin_site = None
    model = None

    def dispatch(self, request, *args, **kwargs):
        request.current_app = self.admin_site.name
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.admin_site.each_context(self.request))
        context['opts'] = self.model._meta
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

class PlaceImportForm(forms.Form):
    def get_source_choices():
        srcs = [
            (s.id, str(s)) for s in Source.objects.all()
        ] + [ (None, '(none)') ]
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

    source_file = forms.FileField(
        label = _('Upload a spreadsheet to import (.csv format only)'),
        required = True,
    )

class PlaceImportConfirmForm(forms.Form):
    pass

class PlaceImportAdminView(AdminViewMixin, FormView):
    template_name = 'admin/import/import.html'
    form_class = PlaceImportForm
    model = Place
    #success_url = reverse_lazy('admin:')

    def get_context_data(self):
        ctx = super().get_context_data()
        inv_cols, misc_cols = get_inverse_colmaps()
        ctx.update({
            'inv_colmaps': mark_safe(json.dumps(inv_cols)),
            'misc_cols': mark_safe(json.dumps(misc_cols)),
        })
        return ctx
    
class PlaceImportAdminConfirmView(FormView, AdminViewMixin):
    template_name = 'admin/import/confirm.html'
    model = Place
    
    def get_success_url(self):
        return reverse('admin:featuremap_place_changelist', current_app=self.admin_site.name)

