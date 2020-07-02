from django import apps
from django.contrib.gis.geos import GEOSGeometry
from django.db import transaction

from featuremap import models

import logging
logger = logging.getLogger(__name__)

class BaseMapField:
    """ Represents a mapping of a raw field name to field on the Dataset's base model """
    needs_row = False
    
    def __init__(self, base_model, model_field):
        self.model = base_model
        self.model_field = model_field
    
    def apply_to_model(self, model_instance, value):
        setattr(model_instance, self.model_field, self.get_value(value))
    
    def get_value(self, value):
        return value
    
    def applies_to_model(self, model):
        return model is self.model
    
class AbstractMetadataMapField:
    def apply_to_model(self, inst, value):
        inst.metadata = inst.metadata or {}
        inst.metadata.set_default(self.model_field, self.get_value(value))
        
class BaseMetadataMapField(BaseMapField, AbstractMetadataMapField):
    pass

class RelatedMapField(BaseMapField):
    """
    Represents a mapping of a raw field name to a field on a related model.
    (s) to base model or other related models.
    """
    def __init__(self, related_model, model_field, fk_field, base_model, separator=None):
        super().__init__(related_model, model_field)
        self.base_model = base_model # related model class
        self.fk_field = fk_field # foreign key field on base model
        self.separator = separator
        
    

class RelatedMetadataMapField(RelatedMapField, AbstractMetadataMapField):
    pass

class StaticMapField(BaseMapField):
    """ Represents a relationship which applies to all models """
    model = None
    def __init__(self, model_field, value):
        self.model_field = model_field
        self.value = value

    def applies_to_model(self, model):
        try:
            f = model._meta.get_field(self.model_field)
        except Exception:
            return False
        return True
    
    def get_value(self, value):
        return self.value

class FilterMapField(BaseMapField):
    """ Multiple raw fields can be combined/processed into a single output field (eg. coordinates) """ 
    needs_row = True
    
    def __init__(self, base_model, model_field):
        self.model = base_model
        self.model_field = model_field
        
    def get_value(self, raw_row):
        return self.do_filter(raw_row)

    def do_filter(self, row):
        pass

def wkt_point(x, y, srid):
    return "SRID=%d;POINT(%f %f)" % (int(srid), float(x), float(y))

class LocationFilterMapField(FilterMapField):
    """ Transform raw fields containing coordinates into a GEOSGeometry (for location field) """
    def __init__(self, base_model, model_field, x_field=None, y_field=None, wkt_field=None, srid=4326):
        super().__init__(base_model, model_field)
        self.x_field = x_field
        self.y_field = y_field
        self.wkt_field = wkt_field
        self.srid = srid
    
    def do_filter(self, row):
        # returns a GEOSGeometry or None for given row's location, clean up the original attributes as well
        try:
            location_wkt = ''
            #do_flip = False # whether to swap x and y in transformed geometry
            if self.wkt_field and self.wkt_field in row:
                # eg. geonoma has data already in WKT, WGS84 projection
                location_wkt = row.pop(self.wkt_field, self.srid)
            else:
                # try construct a WKT from the coordinates
                location_wkt = wkt_point(row.pop(self.x_field), row.pop(self.y_field), self.srid)
    
            geom = GEOSGeometry(location_wkt, srid=self.srid)
            if self.srid != 4326:
                #print('attempt transform from srid %d to %d' % (geom.srid, 4326))
                geom.transform(4326)
                print('transform %s to %s' % (location_wkt, geom.wkt))
            else:
                print('got geometry: %s' % location_wkt)
            return geom
    
        except Exception as e:
            #print(e)
            return None
        
"""
f10781_placenames_colmap = {
    "ID": "source_ref",
    "name": RelatedMapField(models.Word, 'lexeme', 'place', models.Place),
    "english name": RelatedMapField(models.Word, 'desc', 'place', models.Place),
    "WA 250k map ref": BaseMetadataMapField(models.Place, 'WA 250k map ref'),
    "type": BaseMapField(models.Place, 'category'),
    "country": RelatedMapField(models.Language, 'name', 'language', models.Word, separator=","),
    "contacts": BaseMetadataMapField(models.Place, 'contacts'),
    "registered site": BaseMetadataMapField(models.Place, 'registered site'),
    "source": BaseMetadataMapField(models.Place, 'source contact'),
    "comments": BaseMapField(models.Place, 'desc'),
    
    # and filters can be with whatever name...
    "filter_location": LocationFilterMapField(models.Place, 'location', x_field='north', y_field='east', srid=28350),
}
"""

class ValueBase:
    def __init__(self, value):
        self.value = value
        
    def resolve(self, row):
        return self.value
    
class Ref:
    def __init__(self, target_path):
        self.value = target_path
        
    def get_target(self, map):
        path = self.value.split("/")
        for item in path:
            map = map[item]
        return map

class RawField(ValueBase):
    def __init__(self, value, unique=False, separator=None):
        self.value = value
        self.unique = unique
        self.separator = separator
        
    def resolve(self, row):
        val = row.get(self.value, None)
        if self.separator and isinstance(val, str):
            val = [s.trim() for s in val.split(self.separator)]
            if len(val) == 1:
                val = val[0]
            if len(val) == 0:
                val = ''
        return val
    
class ValueLiteral(ValueBase):
    pass
    
class JsonPassthru(list):
    def resolve(self, row):
        return {field: row[field] for field in self} 
        
class ChildRelation(dict):
    pass

class ParentRelation(dict):
    pass

class ModelMap(dict):
    def __init__(self, value, base_model):
        super().__init__(value)
        self.base_model = base_model

class Dataset:
    """ builds a set of model instances with relationships """
    def __init__(self, model_map, rows=None):
        self.model = model_map.base_model
        self.data_rows = {}
        self.instances = {}
        self.colmap = model_map
        if rows:
            for row in rows:
                self.ingest_row(row)
                
    def build_instance(self, model, row, map):
        values = {
            field_name: field.get_value(row)
            for field_name, field in map
        }
        return model(**values)
    
    def ingest_instance(self, model, item):
        model_insts = self.instances.setdefault(model, [])
        model_insts.append(item)
        
    def ingest_row(self, row, source, try_update=False):
        """ remap row (dict of raw_field : value) into dataset, grouped by model name """
        if isinstance(source, str):
            source = models.Source.objects.get_or_create(name=source)
        
        # recursively build the model structure
        def build_model_layer(map, model, level):
            return_multiple = 1
            
            values = {
                "source": source,
            }
            dependents = {}
            #dependencies = {}
            for field, fmap in level:
                val = None
                if isinstance(fmap, (ValueBase, JsonPassthru)):
                    val = fmap.resolve(row)
                elif isinstance(fmap, FilterMapField):
                    val = fmap.do_filter(row)
                elif isinstance(fmap, ChildRelation):
                    # the model "field" is expected to be a related_name (ie. reverse of a ForeignKey)
                    through_model = model._meta.get_field(field).field.model
                    
                    # build a list of child records, they are saved at the end in the correct order
                    childs = build_model_layer(map, through_model, fmap)
                    dependents[field] = childs
                elif isinstance(fmap, ParentRelation):
                    # field must be a ForeignKey
                    parent_model = model._meta.get_field(field).related_model
                    
                    #if isinstance(level, ChildRelation):
                    # handle the to-many side of things (ie. multiple "parents" --> multiple through records)
                    val = build_model_layer(map, parent_model, fmap)
                    #dependencies[parent_model] = val
                
                if isinstance(val, list):
                    # multiple values for this field: return multiple records
                    return_multiple = max(return_multiple, len(val))
            
            if not isinstance(model, models.BaseSourcedModel):
                values.pop('source')
                values.pop('source_ref', None)
            
            instances = []
            for i in range(return_multiple):
                record = {}
                for field, val in values.items():
                    if isinstance(val, list):
                        if len(val) == return_multiple:
                            record[field] = val[i]
                        else:
                            record[field] = ", ".join(val)
                    else:
                        record[field] = val
                
                # now instantiate & save base model
                inst = model(**record)
                inst.save()
                
                self.ingest_instance(model, inst)
                
                # now associate the child records
                for field, childs in dependents.items():
                    rel = getattr(model, field) # get the RelatedManager for the reverse foreignkey
                    if not isinstance(childs, list):
                        rel.add(childs)
                    else:
                        rel.add(*childs)
                        
                instances.append(inst)
            return instances
        
        # now create the relational data structure from the row by recursing into the relation map
        build_model_layer(self.colmap, self.model, self.colmap)
        
    def bulk_ingest(self, rows, source, batch_size=100):
        """ Load raw data rows and relationalise them in bulk """
        rows = iter(rows)
        count = 0
        while True:
            row = None
            
            with transaction.atomic():
                while True:
                    row = next(rows)
                    self.ingest_row(row, source)
                    if count % batch_size == 0:
                        break
                    
            if row is None:
                break
        
        models = ''
        for m, l in self.instances:
            models += '%s (%d), ' % (m.__name__, len(l))
        logger.info("Imported instances: %s" % models[:-2])
