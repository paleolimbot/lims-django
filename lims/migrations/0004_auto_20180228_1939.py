# Generated by Django 2.0.1 on 2018-02-28 23:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lims', '0003_auto_20180228_1814'),
    ]

    operations = [
        migrations.AddField(
            model_name='locationtag',
            name='comment',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='sampletag',
            name='comment',
            field=models.TextField(blank=True),
        ),
    ]