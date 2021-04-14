from django.test import TestCase

from dataset import ModelColMap
from models import ImportDefinition
from featuremap import models
from mappings import f10781_placenames_csv

def MappingSerialisationTestCase(TestCase):
    def setUp(self):
        ImportDefinition.objects.create(name='f10781', desc='Test case 10781 import', mapping=f10781_placenames_csv)
        ImportDefinition.objects.create(name='emptyTest', desc='Nothing here', mapping=ModelColMap({}, base_model=None))
    
    def test_map_serialise(self):
        colmap = ModelColMap({"test": RawField('test_field')}, models.Place)
        self.assertEqual(colmap.to_json(), '')
        f10781 = ImportDefinition.objects.get(name='f10781')
        self.assertEqual(f10781.mapping, f10781_placenames_csv)

def ItemUpdateTest(TestCase):
    def setUp(self):
        pass