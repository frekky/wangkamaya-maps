from .dataset import ModelMap, RawField, LocationFilterMapField, ChildRelation, ParentRelation, JsonPassthru, ValueLiteral
from . import update

from featuremap import models

related_word = update.get_find_matching_by_source(models.Word)
related_place = update.get_find_matching_by_source(models.Place)


f10781_placenames_map = ModelMap({
    "category": RawField("type"),
    "location": LocationFilterMapField(models.Place, 'location', x_field='north', y_field='east', srid=28350),
    "desc": RawField("comments"),
    "source_ref": RawField("ID", unique=True),
    "names": ChildRelation({
        # Word
        "name": RawField("name"),
        "desc": RawField("english name"),
        "source_ref": RawField("ID", unique=True),
        "language": ParentRelation({
            "name": RawField("country", unique=True, separator=","), # this will create duplicate Words pointing to different languages
        }, find_related=update.find_matching_lang),
    }, find_related=related_word),
    "metadata": JsonPassthru([
        "WA 250k map ref",
        "contacts",
        "source",
        "registered site",
        "country",
    ]),
}, models.Place, find_related=related_place)

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
        }, find_related=update.find_matching_lang),
    }, find_related=related_word),
}, models.Place, find_related=related_place)

# for https://catalogue.data.wa.gov.au/dataset/geographic-names-geonoma
geographic_names_geonoma_lgate = ModelMap({
    "category": RawField("feature_class_description"),
    "source_ref": RawField("feature_number"),
    "location": LocationFilterMapField(models.Place, "location", wkt_field="geometry", srid=4326),
    "names": ChildRelation({
        "name": RawField("geographic_name"),
        "language": ParentRelation({
            "name": ValueLiteral("English"),
        }, find_related=update.find_matching_lang)
    }, find_related=related_word),
    "metadata": JsonPassthru([
        "zone",
        "feature_class",
        "northing",
        "easting",
        "longitude",
        "latitude",
    ]),
}, models.Place, find_related=related_place)

# dict of map codes to ModelMaps
mappings = {
    '10781_placenames_csv': f10781_placenames_map,    
    '13831_nyiyaparli_placenames_geocsv': f13831_nyiyaparli_placenames_map,
    'geographic_names_geonoma_lgate': geographic_names_geonoma_lgate,
}