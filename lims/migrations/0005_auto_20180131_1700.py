# Generated by Django 2.0.1 on 2018-01-31 21:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lims', '0004_auto_20180131_1647'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children', to='lims.Location'),
        ),
        migrations.AlterField(
            model_name='sample',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children', to='lims.Sample'),
        ),
    ]