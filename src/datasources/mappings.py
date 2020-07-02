from .dataset import ModelMap, RawField, LocationFilterMapField, ChildRelation, ParentRelation, JsonPassthru, ValueLiteral
from . import update

from featuremap import models 

f10781_placenames_map = ModelMap({
    "category": RawField("type"),
    "location": LocationFilterMapField(models.Place, 'location', x_field='north', y_field='east', srid=28350),
    "desc": RawField("comments"),
    "source_ref": RawField("ID", unique=True),
    "names": ChildRelation({
        # Word
        "lexeme": RawField("name"),
        "desc": RawField("english name"),
        "source_ref": RawField("ID", unique=True),
        "language": ParentRelation({
            "name": RawField("country", unique=True, separator=","), # this will create duplicate Words pointing to different languages
        }, find_related=update.find_matching_lang),
    }, find_related=update.get_find_matching_by_source(models.Word)),
    "metadata": JsonPassthru([
        "WA 250k map ref",
        "contacts",
        "source",
        "registered site",
        "country",
    ]),
}, models.Place)

f13831_nyiyaparli_placenames_map = ModelMap({
    "category": RawField("type"),
    "source_ref": RawField("fid"),
    "location": LocationFilterMapField(models.Place, 'location', wkt_field="WKT", srid=4326),
    "names": ChildRelation({
        # Word
        "name": RawField("name"),
        "source_ref": RawField("fid"),
        "language": ParentRelation({
            "name": ValueLiteral("Nyiyaparli"),
        }, find_related=update.get_find_matching_by_source(models.Word)),
    }),
}, models.Place)


# dict of map codes to ModelMaps
mappings = {
    '10781_placenames_csv': f10781_placenames_map,    
    '13831_nyiyaparli_placenames_geocsv': f13831_nyiyaparli_placenames_map,
}