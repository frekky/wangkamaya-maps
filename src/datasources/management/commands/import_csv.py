from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.gis.geos import GEOSGeometry

import csv
from featuremap.models import Place
from datasources.update import find_matching_place

class Command(BaseCommand):
    help = 'Import a CSV file to the database'

    def add_arguments(self, parser):
        parser.add_argument('filename')
        parser.add_argument('--srid', nargs=1, type=int, default=None,
                            help='Spatial Reference ID, default is 4326 for WGS84')
        parser.add_argument('--source-desc', nargs=1,
                            help='Human description of data source')
        parser.add_argument('--update', action='store_true',
                            help='Update previously imported data with matching source')

    def handle(self, *args, **options):
        #print(args, options)
        #if 'srid' in options and options['srid'] != 4326:
        #    raise CommandError('Must use WGS84 projection, reprojection not implemented yet')
        file = options['filename']
        srid = options['srid']
        if srid is not None:
            srid = srid[0]
        else:
            srid = 4326
        source_desc = options['source_desc'][0] if 'source_desc' in options else file
        import_places(file, source_desc, srid, options['update'])

# map of columns: db field name -> spreadsheet name
## geonoma values
column_map = {
    'name_eng':     'geographic_name',
    'place_type':   'feature_class_description',
    'location__wkt':     'geometry',
    'source_id':    'feature_number',
}

discard_cols = ['northing', 'easting', 'longitude', 'latitude', 'zone', 'geometry']


# for other custom data
column_map = {
    'name':         'name',
    'name_eng':     'english name',
    'place_type':   'type',
    'location__northing': 'north',
    'location__easting': 'east',
    'source_id':    'ID',
    'lang':         'country',
    'desc':         'comments',
}

discard_cols = ['name', 'english name', 'north', 'east', 'ID', 'country']

# for custom map data
#column_map = {
#    'name':         'name',
#    'place_type':   'type',
#    'location__lat': 'Y',
#    'location__lng': 'X',
#    'source_id':    'fid',
#    'lang':         'lang',
#}
#
#discard_cols = ['name', 'X', 'Y', 'fid', 'desc']



def process_cols(colmap, discard_cols, src):
    dst = {}
    for dstcol in colmap:
        dst[dstcol] = src[colmap[dstcol]]
    for d in discard_cols:
        if d in src:
            del src[d]
    return dst

def wkt_point(x, y, srid):
    return "SRID=%d;POINT(%f %f)" % (int(srid), float(x), float(y))

# returns a GEOSGeometry or None for given row's location, clean up the original attributes as well
def parse_location(row, src_srid):
    try:
        location_wkt = ''
        do_flip = False # whether to swap x and y in transformed geometry
        if 'location__wkt' in row:
            # eg. geonoma has data already in WKT, WGS84 projection
            location_wkt = row.pop('location__wkt', src_srid)
        else:
            # try construct a WKT from the coordinates
            if 'location__lat' in row:
                # eg. EPSG:4326 (wgs84)
                location_wkt = wkt_point(row.pop('location__lng'), row.pop('location__lat'), src_srid)
            elif 'location__northing' in row:
                # eg. EPSG:28350 (gda94 zone 50)
                location_wkt = wkt_point(row.pop('location__northing'), row.pop('location__easting'), src_srid)
                do_flip = True # why? weird bug in GEOS seems to put transformed coords backwards
            else:
                raise TypeError('no location defined')

        geom = GEOSGeometry(location_wkt, srid=src_srid)
        if src_srid != 4326:
            #print('attempt transform from srid %d to %d' % (geom.srid, 4326))
            geom.transform(4326)
            if do_flip:
                geom.coords = geom.coords[::-1]
            print('transform %s to %s' % (location_wkt, geom.wkt))
        else:
            print('got geometry: %s' % location_wkt)
        return geom

    except Exception as e:
        #print(e)
        return None

# try to import a row: raises error on fail, False if new row and True if updated
def import_csv_row(row, update, source_desc, src_srid):
    # each row is a dict
    vals = process_cols(column_map, discard_cols, row)
    vals.setdefault('source', source_desc)

    # try to convert the location somehow
    vals['location'] = parse_location(vals, src_srid)

    vals['data'] = row # store all other data we have in the data column, for safekeeping

    # note: update is slow, especially when there's a lot of data already
    if update:
        pqs = find_matching_place(source_desc, vals['source_id'])
        if pqs is not None:
            pqs.update(**vals)
            return True

    p = Place(**vals)
    p.save()
    print("New place '%s'" % p)
    return False

BATCH_SIZE = 100
def import_places(filename, source_desc, srid, update=False):
    with open(filename, newline='') as csvfile:
        total_rows = 0
        new_rows = 0
        reader = csv.DictReader(csvfile)

        while True:
            row = None
            # work in batches of BATCH_SIZE
            with transaction.atomic():
                while True:
                    row = next(reader, None)
                    if row is None:
                        break

                    if import_csv_row(row, update, source_desc, srid) == False:
                        new_rows += 1
                    total_rows += 1

                    if total_rows % BATCH_SIZE == 0:
                        break
            if row is None:
                break

        # got to end of csv file
        print("Import %d rows total, %d new rows / %d updated" % (total_rows, new_rows, total_rows - new_rows))



