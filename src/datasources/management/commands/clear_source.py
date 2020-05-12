from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from featuremap.models import Place

class Command(BaseCommand):
    help = 'Delete records from a given source (ie. to clean up database)'

    def add_arguments(self, parser):
        parser.add_argument('--del', nargs=1,
                            help='Human description of data source, case-sensitive')
        parser.add_argument('--list', action='store_true',
                            help='List available sources in database')

    def handle(self, *args, **options):
        if options['list']:
            r = 'Sources currently in database: (use --del "source name" to clear)\n'
            for row in Place.objects.distinct('source').values('source').iterator():
                num = Place.objects.filter(source=row['source']).count()
                r += "'%s' (%d rows)\n" % (row['source'], num)
            return r

        if options['del'] is None:
            raise CommandError("Please specify a source to delete, use --list to see available ones")


        source_desc = options['del'][0]
        num_rows = Place.objects.filter(source=source_desc).delete()[0]
        print("Deleted %d rows with source='%s'" % (num_rows, source_desc))
