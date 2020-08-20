from django.core.management.base import BaseCommand, CommandError

import csv
from datasources import dataset
from datasources.mappings import mappings
from featuremap.models import Source

class Command(BaseCommand):
    help = 'Import a CSV file to the database'

    def add_arguments(self, parser):
        parser.add_argument('filename')
        parser.add_argument('type', help='Type of data to import, one of: %s' % ", ".join(mappings.keys()))
        parser.add_argument('-s', '--source-desc', help='Description of data source being imported')
        parser.add_argument('-u', '--update', action='store_true',
                            help='Update previously imported data with matching source (slow)')

    def handle(self, *args, **options):
        colmap = mappings.get(options['type'], None)
        if colmap is None:
            raise CommandError("Data type must be one of: %s" % ", ".join(mappings.keys()))
        
        filename = options['filename']
        source_desc = options['source_desc']
        if not source_desc:
            source_desc = "Imported from file '%s' datatype '%s' using manage.py" % (filename, options['type'])
        
        try:
            source = Source.objects.get(name__iexact=options['type'])
        except Source.DoesNotExist:
            source = Source(name=options['type'], description=source_desc)
            source.save()
        
        ds = dataset.Dataset(colmap)
        with open(filename, newline='') as csvfile:
            total_rows = 0
            new_rows = 0
            reader = csv.DictReader(csvfile)
            ds.bulk_ingest(reader, source)
