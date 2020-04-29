# Generated by Django 3.0.5 on 2020-04-29 03:19

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('featuremap', '0002_auto_20200429_0220'),
    ]

    operations = [
        migrations.AddField(
            model_name='place',
            name='date_added',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='place',
            name='date_changed',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='place',
            name='location_desc',
            field=models.CharField(blank=True, max_length=500, verbose_name='Description of location'),
        ),
        migrations.AddField(
            model_name='place',
            name='source_id',
            field=models.CharField(blank=True, max_length=20, verbose_name='Data source feature id'),
        ),
        migrations.AlterField(
            model_name='place',
            name='data',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, verbose_name='Additional data'),
        ),
    ]
