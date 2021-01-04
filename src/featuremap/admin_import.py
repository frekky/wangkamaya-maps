from django.contrib import admin
from django import forms
from django.urls import reverse
from django.views.generic.edit import FormView
from django.utils.translation import gettext_lazy as _

from featuremap.models import Place, Source
from .models import ImportDefinition
from .mappings import mappings

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

class PlaceImportForm(forms.Form):
    map_base = forms.ChoiceField(
        label = _('Base field mapping'),
        required = True,
        choices = get_mapping_choices(),
    )

    source = forms.ChoiceField(
        label = _('Existing source to update'),
        required = False,
        choices = [
            #(s.id, s.name) for s in Source.objects.filter(srcfile__isnull=False)
        ],
    )

    source_file = forms.FileField(
        label = _('Upload a spreadsheet to import (.csv format only)'),
        required = True,
    )

class PlaceImportConfirmForm(forms.Form):
    pass

class PlaceImportAdminView(FormView):
    admin_site = None
    template_name = 'admin/import/import.html'
    form_class = PlaceImportForm
    #success_url = reverse_lazy('admin:')
    
class PlaceImportAdminConfirmView(FormView):
    admin_site = None
    template_name = 'admin/import/confirm.html'
    
    def get_success_url(self):
        return reverse('admin:featuremap_place_changelist', current_app=self.admin_site.name)

