""" initial migration to ensure required PostgreSQL extensions are loaded """

from django.conf import settings
from django.contrib.postgres.operations import CreateExtension
from django.db import migrations

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        CreateExtension('postgis'),
        CreateExtension('citext'),
    ]
