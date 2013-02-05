from django.db import models
from django.template.loaders.cached import Loader as CachedLoader
from django.template.loader import find_template
import reversion


## aseering 11/29/2011
## HACK to generate a warning on deferred field evaluation
from esp.utils import deferred_notifier

""" A template override model that stores the contents of a template in the database. """
class TemplateOverride(models.Model):

    name = models.CharField(max_length=255, help_text='The filename (relative path) of the template to override.')
    content = models.TextField()
    version = models.IntegerField()
    
    class Meta:
        unique_together = (('name', 'version'), )
    
    def __unicode__(self):
        return 'Ver. %d of %s' % (self.version, self.name)
    
    def next_version(self):
        qs = TemplateOverride.objects.filter(name=self.name)
        if qs.exists():
            return qs.order_by('-version').values_list('version', flat=True)[0] + 1
        else:
            return 1
    
    def save(self, *args, **kwargs):
        #   Never overwrite; save a new copy with the version incremented.
        self.version = self.next_version()

        #   Reset all Django template loaders
        #   (our own template loader will be reset through the caching API)
        from django.template.loader import template_source_loaders
        from django.template.loaders.cached import Loader as cached_loader
        for tloader in filter(lambda x: isinstance(x, cached_loader), template_source_loaders):
            tloader.reset()

        super(TemplateOverride, self).save(*args, **kwargs)

from esp.utils import get_user
