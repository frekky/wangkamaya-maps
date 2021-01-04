from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.gis.geos import GEOSGeometry

raise NotImplementedError('Text import requires re-coding, not currently functional, sorry')

from featuremap.models import Place, Language

from datasources.update import find_matching_place

# map of DB fields to eventual txt fields
column_map = {
    'name':         'lx',
    'name_eng':     'de',
    'place_type':   'sd', # mostly "Names and placenames"
    'desc':         'ee',
    'lang':         'ue',
    'source_id':    '_seq',
}

discard_cols = ['_name', '_seq']


class Command(BaseCommand):
    help = 'Import specifically formatted text files (maybe data exported from Toolbox?)'

    def add_arguments(self, parser):
        parser.add_argument('filename')
        parser.add_argument('--srid', nargs=1, type=int, default=4326,
                            help='Spatial Reference ID, default is 4326 for WGS84')
        parser.add_argument('--source-desc', nargs=1,
                            help='Human description of data source')
        parser.add_argument('--update', action='store_true',
                            help='Update previously imported data with matching source')
        parser.add_argument('--cols', nargs='+',
                            help='column mappings in format txt_field:db_field')
        parser.add_argument('--default', nargs='+',
                            help='default values for db fields, eg. --default lang:Yinhawangka "field:With Spaces" [...]')

    def handle(self, *args, **options):
        print(args, options)
        return
        if 'srid' in options and options['srid'] != 4326:
            raise CommandError('Must use WGS84 projection, reprojection not implemented yet')
        filename = options['filename']
        source_desc = options['source_desc'][0] if options['source_desc'] is not None else ''
        with open(filename, mode='rt', newline='') as txtfile:
            import_places(txtfile, source_desc, options['update'],
                          get_col_map(options['cols']), get_defaults(options['default']))

def get_defaults(defs_args):
    d = {}
    if defs_args is None:
        return d
    for s in defs_args:
        col, val = s.split(":", maxsplit=1)
        d[col] = val
    return d

def get_col_map(cols_args):
    if cols_args is None:
        return column_map

    cols = column_map.copy()
    for a in cols_args:
        dst, src = cols_args.split(":")
        cols[dst] = src
    return cols

def process_cols(colmap, discard_cols, src):
    dst = {}
    for dstcol in colmap:
        if colmap[dstcol] in src:
            dst[dstcol] = src[colmap[dstcol]]
    for d in discard_cols:
        if d in src:
            del src[d]
    return dst


# reads one record from text file and returns captured fields as a dict
def read_record(txtfile, data_defaults={}):
    # read some number of blank lines, then record name, then fields
    found_record = False
    data = {}
    data.update(data_defaults)
    field_name = ''
    while True:
        line = txtfile.readline()
        if line == '' or (found_record and line == '\n'):
            print('got eof line="%s"' % line)
            # got EOF
            break
        line = line.strip()

        if not found_record:
            if line != '':
                print('found record line="%s"' % line)
                found_record = True
                # name is first line, may start with \lx
                data['lx'] = line.lstrip("\\lx ")
            continue
        # following non-blank lines are fields and data

        if line[0] == '\\':
            field_name, val = line[1:].split(sep=' ', maxsplit=1)
            data[field_name] = val
        else:
            data[field_name] += line

    if not found_record:
        return None
    return data


def import_places(txtfile, source_desc='', update=False, colmap=column_map, defs={}):
    file_desc = txtfile.readline().strip()
    file_date = txtfile.readline().strip()

    # from https://kite.com/python/answers/how-to-remove-all-non-alphanumeric-characters-from-a-string-in-python
    file_desc = "".join(filter(str.isalnum, file_desc))

    if source_desc == '':
        source_desc = "".join(file_desc.split()) + '-toolbox_txt'

    defs.update({
        '_file_title': file_desc,
        '_file_date': file_date,
    })

    num_records = 0
    num_updates = 0
    with transaction.atomic():
        while True:
            row = read_record(txtfile, defs)
            if row is None:
                break

            row['_seq'] = str(num_records)
            vals = process_cols(colmap, discard_cols, row)
            vals['source'] = source_desc
            vals['data'] = row
            print(vals)

            num_records += 1
            if update:
                pqs = find_matching_place(source_desc, vals['source_id'])
                if pqs is not None:
                    pqs.update(**vals)
                    num_updates += 1
                    continue
            p = Place(**vals)
            p.save()

    print("Imported/updated %d records (%d already existing)" % (num_records, num_updates))
