from django.db.models import ForeignKey, OneToOneField
from esp.db.forms import AjaxForeignKeyNewformField


class AjaxForeignKey(ForeignKey):

    def __init__(self, *args, **kwargs):
        if 'queryset' in kwargs:
            self.queryset = kwargs['queryset']
        else:
            self.queryset = None

        ForeignKey.__init__(self, *args, **kwargs)


    def get_newform_field(self):
        return AjaxForeignKeyNewformField(field=self)

    def formfield(self, **kwargs):
        defaults = {'form_class': AjaxForeignKeyNewformField,
                    'field': self}

        defaults.update(kwargs)
        return super().formfield(**defaults)


class AjaxOneToOneField(OneToOneField):
    """OneToOneField that renders with the AjaxForeignKey autocomplete widget."""

    def formfield(self, **kwargs):
        defaults = {'form_class': AjaxForeignKeyNewformField,
                    'field': self}

        defaults.update(kwargs)
        return super().formfield(**defaults)
