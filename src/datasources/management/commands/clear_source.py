from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from featuremap.models import Place, Word, Source

class Command(BaseCommand):
    help = 'Delete records from a given source (ie. to clean up database)'

    def add_arguments(self, parser):
        parser.add_argument('--del', nargs=1,
                            help='id of data source to delete')
        parser.add_argument('--list', action='store_true',
                            help='List available sources in database')

    def handle(self, *args, **options):
        if options['list'] or options['del'] is None:
            r = 'Sources currently in database: (use --del "source id" to clear)\n'
            for src in Source.objects.all():
                r += "%s: %s (%s): %d places, %d names\n" % (
                    src.pk, src.name, src.description,
                    Place.objects.filter(source=src).count(),
                    Word.objects.filter(source=src).count()
                )
            return r

        try:
            source_id = options['del'][0]
            source = Source.objects.get(pk=source_id)
        except: # Source.DoesNotExist:
            raise CommandError("Invalid source id '%s'" % source_id)
        
        num_p = Place.objects.filter(source=source).delete()[0]
        num_w = Word.objects.filter(source=source).delete()[0]
        source.delete()
        return "Deleted %d places and %d names with source='%s'" % (num_p, num_w, source.name)
