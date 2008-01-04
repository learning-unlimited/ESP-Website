from django.db.models import ForeignKey, Field
from django.conf import settings
from esp.db.forms import AjaxForeignKeyFormField, AjaxForeignKeyNewformField


class AjaxForeignKey(ForeignKey):

    def __init__(self, *args, **kwargs):
        kwargs['raw_id_admin'] = False
        if 'queryset' in kwargs:
            self.queryset = kwargs['queryset']
        else:
            self.queryset = None

        ForeignKey.__init__(self, *args, **kwargs)


    def get_newform_field(self):
        return AjaxForeignKeyNewformField(field=self)

    def get_manipulator_fields(self, *args, **kwargs):
        return [AjaxForeignKeyFormField(field_name = self.name,
                                        is_required = (not self.blank),
                                        field      = self,
                                        queryset   = self.queryset)]
