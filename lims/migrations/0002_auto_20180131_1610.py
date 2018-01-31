# Generated by Django 2.0.1 on 2018-01-31 20:10

from django.db import migrations, models
import django.db.models.deletion
import lims.models


class Migration(migrations.Migration):

    dependencies = [
        ('lims', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='sample',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='lims.Sample'),
        ),
        migrations.AddField(
            model_name='sample',
            name='published',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='term',
            name='meta',
            field=models.TextField(blank=True, validators=[lims.models.validate_json_tags_dict]),
        ),
    ]