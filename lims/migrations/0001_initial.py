# Generated by Django 2.0.1 on 2018-01-23 14:51

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import lims.geometry


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=55)),
                ('slug', models.SlugField(max_length=55, unique=True)),
                ('description', models.TextField(blank=True)),
                ('recursive_depth', models.IntegerField(default=0, editable=False)),
                ('geometry', models.TextField(blank=True, validators=[lims.geometry.validate_wkt])),
                ('minx', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('maxx', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('miny', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('maxy', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='modified')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children', to='lims.Location')),
                ('user', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='LocationTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=55)),
                ('value', models.TextField(blank=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='modified')),
                ('object', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tags', to='lims.Location')),
            ],
        ),
        migrations.CreateModel(
            name='Sample',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=25)),
                ('slug', models.CharField(editable=False, max_length=55, unique=True)),
                ('description', models.TextField(blank=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='modified')),
                ('collected', models.DateTimeField(verbose_name='collected')),
                ('location', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='lims.Location')),
                ('user', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='SampleTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=55)),
                ('value', models.TextField(blank=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='modified')),
                ('object', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tags', to='lims.Sample')),
            ],
        ),
    ]
