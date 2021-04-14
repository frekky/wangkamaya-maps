"""
Column mappings: ModelColMaps which describe how to construct a set of related model instances from a
set of named input fields (eg. columns from a spreadsheet).

The various relationship types are defined in dataset.py. Filters can be used to combine multiple input
fields into a single output model field.
"""

from .dataset import (ModelColMap, RawField, ConcatRawField, LocationFilter, ChildRelation,
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

landgate_geonoma_full = ModelColMap({
    "category": RawField("FEATURE_CLASS"),
    # SRID 28350 = GDA94 / MGA zone 50
    "location": LocationFilter(east_field='EASTING', north_field='NORTHING', srid=28350),
    "names": ChildRelation({
        "name": RawField("GEOGRAPHIC_NAME", unique=True),
        "desc": RawField("DERIVATION"),
        "language": LanguageRelation({
            "name": ValueLiteral("English"),
        }),
    }),
    "metadata": JsonPassthru([
        "DERIVATION",
        "NAME_TYPE",
        "NAME_APPROVED",
        "FEATURE_STATUS",
        "FEATURE_SIZE",
        "UNITS", # for FEATURE_SIZE
        "POSTCODE",
        "NEAREST_TOWN",
        "PERTH_ROAD_DISTANCE",
        "PERTH_RADIAL_DISTANCE",
        "POPULATION",
        "DATE_OF_CENSUS",
        "MAP_NUMBER",
        "ABS_LGA_NUMBER",
        "LGA_NAME",
        "LOCALITY_NAME",
        "LATITUDE",
        "LONGITUDE",
        "EASTING",
        "NORTHING",
        "ZONE",
        "PRIORITY",
    ]),
}, models.Place, ref_field=RawField("FEATURE_NUMBER"))

discovery_export_places = ModelColMap({
    "names": ChildRelation({
        # on the Word model:
        "name": RawField("descriptiveName"),
        "desc": RawField("description"),
        "language": LanguageRelation({
            "name": ValueLiteral("Not Specified"),
        }),
    }),
    "category": RawField("type"),
    "location_desc": ConcatRawField([
        ('City', 'city'),
        ('State', 'state'),
    ]),
    "location": LocationFilter(lat_field='latitude', lng_field='longitude', srid='4326'),
    "metadata": JsonPassthru([
        'createdAt',
        'createdBy',
        'g_foundCount',
        'latitude',
        'longitude',
        'modifiedAt',
        'modifiedBy',
        'name',
        'nameDisplay',
        'uuid',
    ])
}, models.Place, ref_field=RawField("g_foundCount"))

# dict of map codes to ModelMaps
mappings = {
    '10781: placenames data pg5-12': f10781_placenames_csv,   
    '10781: Ngarla map pg4': f10781_techela_map, 
    '13831: Nyiyaparli placenames': f13831_nyiyaparli_placenames_map,
    'Geographic Names GEONOMA LGATE (free)': geographic_names_geonoma_lgate,
    'Landgate GEONOMA (premium extract)': landgate_geonoma_full,
    'Discovery Database export': discovery_export_places,
}

