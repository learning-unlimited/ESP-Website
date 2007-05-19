from django.db.models import ForeignKey, Field
from django.conf import settings
from esp.db.forms import AjaxForeignKeyFormField


class AjaxForeignKey(ForeignKey):

    def __init__(self, *args, **kwargs):
        #kwargs['raw_id_admin'] = True
        ForeignKey.__init__(self, *args, **kwargs)

    def contribute_to_class(self, cls, name):
        media_url = settings.MEDIA_URL
        yui_url = media_url + 'scripts/yui/'
        
        if cls._meta.admin:
            js_list = [
                'yahoo/yahoo-min.js',
                'yahoo-dom-event/yahoo-dom-event.js',
                'dom/dom-min.js',
                'connection/connection-min.js',
                'animation/animation-min.js',
                'autocomplete/autocomplete-min.js',
                ]

            cls._meta.admin.js += [ yui_url+js for js in js_list ]
            cls._meta.admin.js.append('http://www.json.org/json.js')

   #         cls._meta.admin.js = list(set(cls._meta.admin.js))
            
        ForeignKey.contribute_to_class(self, cls, name)

    def get_manipulator_fields(self, *args, **kwargs):
        return [AjaxForeignKeyFormField(field_name = self.name,
                                        field      = self)]
