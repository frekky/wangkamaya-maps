"""
Column mappings: ModelColMaps which describe how to construct a set of related model instances from a
set of named input fields (eg. columns from a spreadsheet).

The various relationship types are defined in dataset.py. Filters can be used to combine multiple input
fields into a single output model field.
"""

from .dataset import (ModelColMap, RawField, LocationFilter, ChildRelation,
                      JsonPassthru, ValueLiteral, LanguageRelation)
from featuremap import models

f10781_placenames_csv = ModelColMap({
    "category": RawField("type"),
    "location": LocationFilter(north_field='north', east_field='east', srid=28350),
    "desc": RawField("comments"),
    "names": ChildRelation({
        # Word
        "name": RawField("name", unique=True),
        "desc": RawField("english name"),
        "language": LanguageRelation({
            "name": RawField("country", unique=True, separator=","), # this will create duplicate Words pointing to different languages
        }),
    }),
    "metadata": JsonPassthru([
        "WA 250k map ref",
        "contacts",
        "source",
        "registered site",
        "country",
    ]),
}, models.Place, ref_field=RawField("ID"))

f10781_techela_map = ModelColMap({
    "category": RawField("type"),
    "desc": RawField("name_eng"),
    "location": LocationFilter(lat_field='Y', lng_field='X', srid=4326),
    "names": ChildRelation({
        # Word
        "name": RawField("name"),
        "language": LanguageRelation({
            "name": RawField("lang", unique=True),
        })
    }),
}, models.Place, ref_field=RawField("fid"))

f13831_nyiyaparli_placenames_map = ModelColMap({
    "category": RawField("type"),
    "location": LocationFilter(wkt_field="WKT", srid=4326),
    "names": ChildRelation({
        # Word
        "name": RawField("name", unique=True),
        "language": LanguageRelation({
            "name": ValueLiteral("Nyiyaparli"),
        }),
    }),
}, models.Place, ref_field=RawField("fid"))

# for https://catalogue.data.wa.gov.au/dataset/geographic-names-geonoma
geographic_names_geonoma_lgate = ModelColMap({
    "category": RawField("feature_class_description"),
    "location": LocationFilter(wkt_field="geometry", srid=4326),
    "names": ChildRelation({
        "name": RawField("geographic_name", unique=True),
        "language": LanguageRelation({
            "name": ValueLiteral("English"),
        }),
    }),
    "metadata": JsonPassthru([
        "zone",
        "feature_class",
        "northing",
        "easting",
        "longitude",
        "latitude",
    ]),
}, models.Place, ref_field=RawField("feature_number"))

# dict of map codes to ModelMaps
mappings = {
    '10781_placenames_csv.1': f10781_placenames_csv,   
    '10781_ngarla_techela_map.1': f10781_techela_map, 
    '13831_nyiyaparli_placenames_geocsv.1': f13831_nyiyaparli_placenames_map,
    'geographic_names_geonoma_lgate.1': geographic_names_geonoma_lgate,
}