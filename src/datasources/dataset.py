from django import apps
from django.contrib.gis.geos import GEOSGeometry
from django.db import transaction
from django.db.models.query import QuerySet
from django.db.models import Q
from django.forms.models import model_to_dict

from featuremap import models

import logging
logger = logging.getLogger(__name__)

class ValueBase:
    unique = False
    def resolve(self, row, index):
        pass

class RawField(ValueBase):
    def __init__(self, value, unique=False, separator=None):
        self.value = value
        self.unique = unique
        self.separator = separator
        
    def resolve(self, row, index):
        val = row.get(self.value, None)
        if self.separator and isinstance(val, str):
            val = [s.strip() for s in val.split(self.separator)]
            if len(val) == 1:
                val = val[0]
            if len(val) == 0:
                val = ''
        return val
    
class ValueLiteral(ValueBase):
    def __init__(self, value):
        self.value = value
        
    def resolve(self, row, index):
        return self.value

class RowNumber(ValueBase):
    def resolve(self, row, index):
        return index

class FilteredField:
    """ Multiple raw fields can be combined/processed into a single output field (eg. coordinates) """
    def __init__(self, *args, **input_fields):
        pass
    
    def calculate(self, values):
        """ calculate the filtered value from the fields in the given input rowv values dict """
        pass
    
class LocationFilter(FilteredField):
    WKT         = 0
    NORTH_EAST  = 1
    LAT_LNG     = 2
    
    """ Transform raw fields containing coordinates into a GEOSGeometry (for location field) """
    def __init__(self, lat_field=None, lng_field=None, wkt_field=None, east_field=None, north_field=None, srid=4326):
        if not (lat_field is None or lng_field is None):
            self.mode = self.LAT_LNG
            self.lat_field = lat_field
            self.lng_field = lng_field
        elif not (east_field is None or north_field is None):
            self.mode = self.NORTH_EAST
            self.north_field = north_field
            self.east_field = east_field
        elif not wkt_field is None:
            self.mode = self.WKT
            self.wkt_field = wkt_field
        else:
            raise NotImplementedError("Please specify the lat/lng, north/east or WKT fields for LocationFilter")
        self.srid = srid
    
    def wkt_point(self, x, y):
        # Note: WKT geographic coordinates are sometimes (Long, Lat) whereas projected coords are (x, y)
        # see https://www.drupal.org/project/geo/issues/511370
        if x and y:
            return "POINT(%f %f)" % (float(x), float(y))
        
    def calculate(self, row):
        # returns a GEOSGeometry or None for given row's location, clean up the original attributes as well
        location_wkt = None
        swap = False
        if self.mode == self.WKT and self.wkt_field in row:
            # eg. geonoma has data already in WKT, WGS84 projection
            location_wkt = row.pop(self.wkt_field)
        elif self.mode == self.LAT_LNG and self.lat_field in row and self.lng_field in row:
            # try construct a WKT from the coordinates
            location_wkt = self.wkt_point(row.pop(self.lng_field), row.pop(self.lat_field))
        elif self.mode == self.NORTH_EAST and self.north_field in row and self.east_field in row:
            location_wkt = self.wkt_point(row.pop(self.north_field), row.pop(self.east_field))
            swap = True
        
        if not location_wkt:
            return None
                
        try:
            geom = GEOSGeometry(location_wkt, srid=self.srid)
            if self.srid != 4326:
                geom.transform(4326)
                if swap:
                    geom.coords = geom.coords[::-1]
                logger.debug('transform srid %d %s to srid %d %s' % (self.srid, location_wkt, geom.srid, geom.wkt))
            else:
                logger.debug('got geometry: %s' % geom.wkt)
            return geom
    
        except Exception as e:
            #print(e)
            return None
    
class JsonPassthru(list):
    unique = False
    def resolve(self, row, index):
        return {field: row[field] for field in self} 
    
class Relation(dict):
    FIND_EXISTING = 1
    SOURCE_UPDATE = 2
    
    def __init__(self, fields, ref_field=None, mode=SOURCE_UPDATE):
        """ value is a dict with keys for each field in the related object """
        self.mode = mode
        super().__init__(fields)
        
        if ref_field:
            ref_field.unique = True
            self["source_ref"] = ref_field
    
    def find_model_instance(self, filter_fields, values, model=None, qs=None):
        """
        Tries to find existing row given a set of search values. Returns iterable of Model instances (eg. QuerySet)
        """
        qs = qs or model.objects.all()
        
        # construct the filter spec
        if self.mode == self.FIND_EXISTING:
            """ find existing objects in DB by searching for matching fields (where unique=True) """
            query = {
                "%s__exact" % field: values[field]
                    for field in filter_fields if field in values
            }
        elif self.mode == self.SOURCE_UPDATE:
            query = {
                'source__exact': values['source'],
                'source_ref__exact': values['source_ref'],
            }
            
        qs = model.objects.filter(**query)
        return qs
    
class ChildRelation(Relation):
    pass

class ParentRelation(Relation):
    pass

class LanguageRelation(ParentRelation):
    """
    Relationship of a word to a language.
    Deals with multiple names (eg. Language.name and Language.alt_names)
    """
    model = models.Language
    def __init__(self, fields):
        super().__init__(fields, mode=Relation.FIND_EXISTING)
    
    def find_language(self, name, model):
        if not name or len(name) < 3:
            return model.default()
        
        try: 
            # look up language by the name provided
            return model.objects.get(name=name)
        except model.DoesNotExist:
            # in case that doesn't work, try searching alternative names
            langs = model.objects.filter(alt_names__contains=[name])
            if langs.count() >= 1:
                return langs[0]
            elif langs.count() > 1:
                logger.warning("Found multiple matching languages for name='%s': %s" % (name, langs))
                return langs[0]
            
        return None
    
    def find_model_instance(self, filter_fields, values, model=None):
        model = model or self.model
        """ returns an iterable (ie. QuerySet) of matching objects """
        if 'name' in values:
            name = values['name'].strip()
            lang = self.find_language(name, model)
            return [lang] if lang else []
        else:
            return (model.default(), )

class ModelColMap(Relation):
    """ Used as the base of a relational model column map, with a base model provided """
    def __init__(self, fields, base_model, ref_field=None, **kwargs):
        super().__init__(fields, ref_field = ref_field or RowNumber(), **kwargs)
        self.base_model = base_model

class Dataset:
    """ builds a set of model instances with relationships """
    def __init__(self, model_map, rows=None, dry_run=False):
        self.model = model_map.base_model
        self.dry_run = dry_run
        
        # track new and updated objects as well as any relationships
        self.new_instances = {}
        self.updated_instances = {}
        self.relationships = {}
        
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
        """ Save a new or updated model instance in the dataset """
        if item._state.adding:
            model_insts = self.new_instances.setdefault(model, list())
        else:
            model_insts = self.updated_instances.setdefault(model, list())
        if not item in model_insts:
            model_insts.append(item)
        
        if not self.dry_run:
            item.save()
            
    def ingest_related(self, related_manager, items):
        """ Save a relationship into the database """
        if not self.dry_run:
            related_manager.add(*items)
        rs = self.relationships.setdefault(related_manager, list())
        rs += items
        
    def ingest_row(self, row, row_index, source=None, try_update=True):
        """ remap row (dict of raw_field : value) into dataset, grouped by model name """
        source_ref = self.colmap['source_ref'].resolve(row, row_index)
            
        def update_model(instance, values):
            for k, v in values.items():
                setattr(instance, k, v)
            return instance
        
        # recursively build the model structure
        def build_model_layer(model, level, path=None):
            path = path or model.__name__
            return_multiple = 1
            values = {}
            fields_unique = []
            dependents = {}

            for field, fmap in level.items():
                val = None
                if isinstance(fmap, (ValueBase, JsonPassthru)):
                    val = fmap.resolve(row, row_index)
                    if fmap.unique:
                        fields_unique.append(field)
                elif isinstance(fmap, FilteredField):
                    val = fmap.calculate(row)
                elif isinstance(fmap, ChildRelation):
                    # the model "field" is expected to be a related_name (ie. reverse of a ForeignKey)
                    through_model = model._meta.get_field(field).field.model
                    
                    # build a list of child records, they are saved at the end in the correct order
                    childs = build_model_layer(through_model, fmap, path=(path + '<-' + field))
                    dependents[field] = childs
                elif isinstance(fmap, ParentRelation):
                    # field must be a ForeignKey
                    parent_model = model._meta.get_field(field).related_model
                    
                    # handle the to-many side of things (ie. multiple "parents" --> multiple through records)
                    val = build_model_layer(parent_model, fmap, path=(path + '->' + field))
                
                if isinstance(val, list):
                    # multiple values for this field: return multiple records
                    return_multiple = max(return_multiple, len(val))
                
                if not val is None:
                    values[field] = val
            
            if hasattr(model, 'source') and hasattr(model, 'source_ref'):
                # ensure the source and source_ref are always provided
                values.setdefault('source', source)
                values.setdefault('source_ref', source_ref)
            
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
                        
                my_ref = record.get('source_ref', None)
                if my_ref:
                    # append per-record reference where row contains list fields
                    record['source_ref'] = str(my_ref) + "_" + str(i)
                
                # try to find existing matching rows
                logger.debug("fields_unique=%s values=%s" % (fields_unique, record))
                
                inst = None
                if try_update or level.mode == Relation.FIND_EXISTING:
                    # try to find an existing record of the current model
                    matches = list(level.find_model_instance(fields_unique, record, model))
                    logger.debug("found matching rows: %s" % str(matches))
                    if len(matches) == 1:
                        if try_update and level.mode == Relation.SOURCE_UPDATE:
                            inst = update_model(matches[0], record)
                        else:
                            inst = matches[0]
                    elif len(matches) > 1:
                        # multiple matching instances: merge them into the new object, saved in the metadata field
                        old_rows = record.setdefault('old_rows', [])
                        for i in matches:
                            if not self.dry_run: 
                                i.delete()
                            old_rows.append(model_to_dict(i))
                
                if not inst:
                    # instantiate & save the record for the model currently being processed
                    inst = model(**record)
                    logger.debug("%s: New instance %s" % (type(inst), str(record)))
                    
                self.ingest_instance(model, inst)
                
                # now associate the child records
                for field, childs in dependents.items():
                    rel = getattr(inst, field) # get the RelatedManager for the reverse foreignkey
                    rel.add(*childs)
                        
                instances.append(inst)
            logger.debug("got instances: %s" % str(instances))
            return instances
        
        # now create the relational data structure from the row by recursing into the relation map
        build_model_layer(self.model, self.colmap)
        
    def bulk_ingest(self, rows, source, batch_size=1, allow_update=True):
        """
        Bulk import data rows into relational database structure. Can update from previously imported sources
        by finding matching rows using source and source_ref.
        """
        if isinstance(source, str):
            source = models.Source.objects.get_or_create(name=source)

        if source._state.adding:
            # ensure source is saved before using it 
            source.save()
            allow_update = False
        
        rows = iter(rows)
        count = 0
        while True:
            row = None
            with transaction.atomic():
                while True:
                    try:
                        row = next(rows)
                    except StopIteration: # there are no more rows
                        row = None
                        break
                
                    self.ingest_row(row, count, source, try_update=allow_update)
                    count += 1
                    if count % batch_size == 0:
                        # commit the transaction once we have processed a batch of rows
                        break
                    
            if row is None:
                break
        
        models = ''
        s = lambda insts: ", ".join("%s (%d)" % (m.__name__, len(l)) for m, l in insts.items())
        
        logger.info("Imported instances: new=[%s], updated [%s]" % (s(self.new_instances), s(self.updated_instances)))

