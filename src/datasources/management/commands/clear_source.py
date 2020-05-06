from django.core.management.base import BaseCommand, CommandError

from featuremap.models import Place

class Command(BaseCommand):
    help = 'Delete records from a given source (ie. to clean up database)'

    def add_arguments(self, parser):
        parser.add_argument('source-desc', nargs=1,
                            help='Human description of data source')

    def handle(self, *args, **options):
        source_desc = options['source-desc'][0]
        num_rows = Place.objects.filter(source=source_desc).delete()[0]
        print("Deleted %d rows with source='%s'" % (num_rows, source_desc))
