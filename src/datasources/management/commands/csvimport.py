from django.core.management.base import BaseCommand, CommandError

import csv
from featuremap.models import Place, Language
from django.contrib.gis.geos import GEOSGeometry

class Command(BaseCommand):
    help = 'Import a CSV file to the database'

    def add_arguments(self, parser):
        parser.add_argument('filename')
        parser.add_argument('--srid', nargs=1, type=int, default=4326,
                            help='Spatial Reference ID, default is 4326 for WGS84')
        parser.add_argument('--source-desc', nargs=1,
                            help='Human description of data source')
        parser.add_argument('--update', action='store_true',
                            help='Update previously imported data with matching source')

    def handle(self, *args, **options):
        print(args, options)
        if 'srid' in options and options['srid'] != 4326:
            raise CommandError('Must use WGS84 projection, reprojection not implemented yet')
        file = options['filename']
        source_desc = options['source_desc'][0] if 'source_desc' in options else file
        import_places(file, source_desc, options['update'])

# map of columns: db field name -> spreadsheet name
column_map = {
    'name_eng':     'geographic_name',
    'place_type':   'feature_class_description',
    'location':     'geometry',
    'source_id':    'feature_number',
}

discard_cols = ['northing', 'easting', 'longitude', 'latitude', 'zone', 'geometry']

def process_cols(colmap, discard_cols, src):
    dst = {}
    for dstcol in colmap:
        dst[dstcol] = src[colmap[dstcol]]
    for d in discard_cols:
        if d in src:
            del src[d]
    return dst

def import_places(filename, source_desc, update=False):
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # each row is a dict
            vals = process_cols(column_map, discard_cols, row)
            vals.setdefault('source', source_desc)
            vals.setdefault('lang', None)
            vals['location'] = GEOSGeometry(vals['location']) # parse WKT to geometry type
            vals['data'] = row # store all other data we have in the data column, for safekeeping
            if update:
                pls = Place.objects.filter(source=source_desc, source_id=vals['source_id'])
                if pls.count() > 1:
                    print("Removing duplicates: %s" % pls)
                    pls.delete()
                elif pls.count() == 1:
                    print("Updating place '%s'" % pls[0])
                    pls.update(**vals)
                    continue

            p = Place(**vals)
            p.save()
            print("New place '%s'" % p)
