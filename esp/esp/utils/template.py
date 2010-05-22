
""" A loader that looks for templates in the override model. """

from django.template.loader import BaseLoader
from django.template import TemplateDoesNotExist

from esp.utils.models import TemplateOverride

class Loader(BaseLoader):
    is_usable = True
    
    def load_template_source(self, template_name, *args, **kwargs):
        qs = TemplateOverride.objects.filter(name=template_name)
        if qs.exists():
            return (qs.order_by('-version').values_list('content', flat=True)[0], None)
        raise TemplateDoesNotExist(template_name)
    load_template_source.is_usable = True
