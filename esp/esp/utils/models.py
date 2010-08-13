from django.db import models
from django.template.loaders.cached import Loader as CachedLoader
from django.template.loader import find_template

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
        #   Try finding a template in order to make sure Django has loaded the template loaders.
        (source, origin) = find_template('main.html')
        
        #   Then grab the template loaders.
        from django.template.loader import template_source_loaders
    
        #   Never overwrite; save a new copy with the version incremented.
        self.id = None
        self.version = self.next_version()
        kwargs['force_insert'] = True
        super(TemplateOverride, self).save(*args, **kwargs)
        
        #   Reset any cached template loaders.
        for loader in template_source_loaders:
            if isinstance(loader, CachedLoader):
                loader.reset()
        
    
    
