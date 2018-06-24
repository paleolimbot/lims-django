# Generated by Django 2.0.1 on 2018-06-24 03:02

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import lims.models
import lims.utils.geometry


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BaseValidator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=55)),
                ('description', models.TextField(blank=True)),
                ('regex', models.TextField(validators=[lims.models.validate_is_a_regex])),
                ('error_message', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='EntryTemplate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=55, unique=True)),
                ('model', models.CharField(default='Sample', max_length=55, validators=[django.core.validators.RegexValidator('^(Sample|SampleTag|Location|LocationTag)$')])),
                ('last_used', models.DateTimeField(auto_now=True, verbose_name='last_used')),
            ],
        ),
        migrations.CreateModel(
            name='EntryTemplateField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('target', models.CharField(max_length=55)),
                ('initial_value', models.TextField(blank=True)),
                ('order', models.IntegerField(default=1)),
            ],
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=55)),
                ('slug', lims.models.SlugIdField(blank=True, max_length=55, unique=True, validators=[django.core.validators.RegexValidator('[A-Za-z0-9._-]*')])),
                ('description', models.TextField(blank=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='modified')),
                ('recursive_depth', models.IntegerField(default=0, editable=False)),
                ('geometry', models.TextField(blank=True, validators=[lims.utils.geometry.validate_wkt])),
                ('minx', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('maxx', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('miny', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('maxy', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children', to='lims.Location')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='LocationTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.TextField(blank=True)),
                ('comment', models.TextField(blank=True)),
                ('meta', models.TextField(blank=True, validators=[lims.models.validate_json_tags_dict])),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='modified')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=55)),
                ('slug', lims.models.SlugIdField(blank=True, max_length=55, unique=True, validators=[django.core.validators.RegexValidator('[A-Za-z0-9._-]*')])),
                ('description', models.TextField(blank=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='modified')),
                ('recursive_depth', models.IntegerField(default=0, editable=False)),
                ('geometry', models.TextField(blank=True, validators=[lims.utils.geometry.validate_wkt])),
                ('minx', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('maxx', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('miny', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('maxy', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children', to='lims.Project')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ProjectTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.TextField(blank=True)),
                ('comment', models.TextField(blank=True)),
                ('meta', models.TextField(blank=True, validators=[lims.models.validate_json_tags_dict])),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='modified')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Sample',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=55)),
                ('slug', lims.models.SlugIdField(blank=True, max_length=55, unique=True, validators=[django.core.validators.RegexValidator('[A-Za-z0-9._-]*')])),
                ('description', models.TextField(blank=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='modified')),
                ('recursive_depth', models.IntegerField(default=0, editable=False)),
                ('geometry', models.TextField(blank=True, validators=[lims.utils.geometry.validate_wkt])),
                ('minx', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('maxx', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('miny', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('maxy', models.FloatField(blank=True, default=None, editable=False, null=True)),
                ('collected', models.DateTimeField(verbose_name='collected')),
                ('published', models.BooleanField(default=False)),
                ('location', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='lims.Location')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children', to='lims.Sample')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lims.Project')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SampleTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.TextField(blank=True)),
                ('comment', models.TextField(blank=True)),
                ('meta', models.TextField(blank=True, validators=[lims.models.validate_json_tags_dict])),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='modified')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Taxonomy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=55)),
                ('slug', models.SlugField(max_length=55)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Term',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=55)),
                ('slug', models.SlugField(max_length=55)),
                ('description', models.TextField(blank=True)),
                ('measured', models.BooleanField(default=False)),
                ('meta', models.TextField(blank=True, validators=[lims.models.validate_json_tags_dict])),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children', to='lims.Term')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lims.Project')),
                ('taxonomy', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='terms', to='lims.Taxonomy')),
            ],
        ),
        migrations.CreateModel(
            name='TermValidator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('term', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='validators', to='lims.Term')),
                ('validator', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lims.BaseValidator')),
            ],
        ),
        migrations.AddField(
            model_name='sampletag',
            name='key',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lims.Term'),
        ),
        migrations.AddField(
            model_name='sampletag',
            name='object',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tags', to='lims.Sample'),
        ),
        migrations.AddField(
            model_name='sampletag',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='projecttag',
            name='key',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lims.Term'),
        ),
        migrations.AddField(
            model_name='projecttag',
            name='object',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tags', to='lims.Project'),
        ),
        migrations.AddField(
            model_name='projecttag',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='locationtag',
            name='key',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lims.Term'),
        ),
        migrations.AddField(
            model_name='locationtag',
            name='object',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tags', to='lims.Location'),
        ),
        migrations.AddField(
            model_name='locationtag',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='location',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lims.Project'),
        ),
        migrations.AddField(
            model_name='location',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='entrytemplatefield',
            name='taxonomy',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='lims.Taxonomy'),
        ),
        migrations.AddField(
            model_name='entrytemplatefield',
            name='template',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fields', to='lims.EntryTemplate'),
        ),
        migrations.AddField(
            model_name='entrytemplate',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='lims.Project'),
        ),
        migrations.AddField(
            model_name='entrytemplate',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='term',
            unique_together={('project', 'taxonomy', 'slug')},
        ),
    ]
