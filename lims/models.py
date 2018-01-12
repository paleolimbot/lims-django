from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse_lazy


class Sample(models.Model):
    name = models.CharField(max_length=25, blank=True)
    slug = models.CharField(max_length=55, unique=True, editable=False)

    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, editable=False)
    created = models.DateTimeField("created", auto_now_add=True)
    modified = models.DateTimeField("modified", auto_now=True)

    collected = models.DateTimeField("collected", blank=True, null=True)
    location = models.CharField(blank=True, max_length=100)

    def get_absolute_url(self):
        return reverse_lazy('lims:sample_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if not self.pk:
            self.set_slug()
        super(Sample, self).save(*args, **kwargs)

    def set_slug(self):
        dt = self.collected if self.collected else self.created if self.created else timezone.now()
        location_slug = slugify(self.location[:10]) if self.location else ""
        user = self.user.username if self.user else ""
        hint = slugify(self.name)

        for date_fun in [self.short_date, self.long_date, self.longest_date]:
            dt_str = date_fun(dt)
            id_str = "_".join(item for item in [user, dt_str, location_slug, hint] if item)
            id_str = id_str[:55]
            other_objects = Sample.objects.filter(slug=id_str)
            if len(other_objects) == 0:
                self.slug = id_str
                return

        self.slug = str(self.pk)

    def short_date(self, dt):
        return str(dt.date())

    def long_date(self, dt):
        return "%sT%s.%s.%s" % (dt.date(), dt.hour, dt.minute, dt.second)

    def longest_date(self, dt):
        return ("%sT%s" % (dt.date(), dt.time())).replace(":", ".")

    def __str__(self):
        return self.slug


class SampleTag(models.Model):
    object = models.ForeignKey(Sample, on_delete=models.CASCADE)
    key = models.CharField(max_length=55)
    value = models.TextField(blank=True)

    created = models.DateTimeField("created", auto_now_add=True)
    modified = models.DateTimeField("modified", auto_now=True)

    def save(self, *args, **kwargs):
        # update parent param modified tag
        self.object.modified = timezone.now()
        super(SampleTag, self).save(*args, **kwargs)

    def __str__(self):
        return '%s="%s"' % (self.key, self.value)