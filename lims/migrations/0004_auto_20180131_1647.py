# Generated by Django 2.0.1 on 2018-01-31 20:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lims', '0003_auto_20180131_1644'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='lims.Location'),
        ),
        migrations.AlterField(
            model_name='location',
            name='recursive_depth',
            field=models.IntegerField(default=0),
        ),
    ]
