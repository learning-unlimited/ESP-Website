from django import forms
from django.forms.models import fields_for_model
from django.apps import apps
from localflavor.us.forms import USStateField, USPhoneNumberField, USStateSelect
from esp.customforms.forms import NameField, AddressField, CustomFileWidget
from esp.utils.forms import DummyField

generic_fields = {
    'textField': {'typeMap': forms.CharField, 'attrs': {'widget': forms.TextInput,}, 'widget_attrs': {'size': '30', 'class': ''}},
    'longTextField': {'typeMap': forms.CharField, 'attrs': {'widget': forms.TextInput,}, 'widget_attrs': {'size': '60', 'class': ''}},
    'longAns': {'typeMap': forms.CharField, 'attrs': {'widget': forms.Textarea,}, 'widget_attrs': {'rows': '8', 'cols': '50', 'class': ''}},
    'reallyLongAns': {'typeMap': forms.CharField, 'attrs': {'widget': forms.Textarea,}, 'widget_attrs': {'rows': '14', 'cols': '70', 'class': ''}},
    'radio': {'typeMap': forms.ChoiceField, 'attrs': {'widget': forms.RadioSelect, }, 'widget_attrs': {'class': ''}},
    'dropdown': {'typeMap': forms.ChoiceField, 'attrs': {'widget': forms.Select, }, 'widget_attrs': {'class': ''}},
    'multiselect': {'typeMap': forms.MultipleChoiceField, 'attrs': {'widget': forms.SelectMultiple, }, 'widget_attrs': {'class': ''}},
    'checkboxes': {'typeMap': forms.MultipleChoiceField, 'attrs': {'widget': forms.CheckboxSelectMultiple, }, 'widget_attrs': {'class': ''}},
    'numeric': {'typeMap': forms.IntegerField, 'attrs': {'widget': forms.TextInput,}, 'widget_attrs': {'class': 'digits '},},
    'date': {'typeMap': forms.DateField,'attrs': {'widget': forms.DateInput,}, 'widget_attrs': {'class': 'ddate ', 'format': '%m-%d-%Y'},},
    'time': {'typeMap': forms.TimeField, 'attrs': {'widget': forms.TimeInput,}, 'widget_attrs': {'class': 'time '},},
    'file': {'typeMap': forms.FileField, 'attrs': {'widget': CustomFileWidget,}, 'widget_attrs': {'class': 'file'},},
    'phone': {'typeMap': USPhoneNumberField, 'attrs': {'widget': forms.TextInput,}, 'widget_attrs': {'class': 'USPhone '}},
    'email': {'typeMap': forms.EmailField, 'attrs': {'max_length': 30, 'widget': forms.TextInput,}, 'widget_attrs': {'class': 'email '}},
    'state': {'typeMap': USStateField, 'attrs': {'widget': USStateSelect}, 'widget_attrs': {'class': ''}},
    'gender': {'typeMap': forms.ChoiceField, 'attrs': {'widget': forms.RadioSelect, 'choices': [('F', 'Female'), ('M', 'Male')]}, 'widget_attrs': {'class': 'gender '}, },
    'radio_yesno': {'typeMap': forms.ChoiceField, 'attrs': {'widget': forms.RadioSelect, 'choices': (('T', 'Yes'), ('F', 'No'))}, 'widget_attrs': {'class': ''}},
    'boolean': {'typeMap': forms.BooleanField, 'attrs': {'widget': forms.CheckboxInput}, 'widget_attrs': {'class': ''}},
    'null_boolean': {'typeMap': forms.NullBooleanField, 'attrs': {'widget': forms.NullBooleanSelect}, 'widget_attrs': {'class': ''}},
    'instructions': {'typeMap': DummyField, 'attrs': {'widget': None}, 'widget_attrs': {'class': ''}},
}

custom_fields = {
    #   field_name: (FieldClass, args, kwargs) for constructing instance of FieldClass
    'address': (AddressField, (), {'class': ''}),
    'name': (NameField, (), {'class': ''})
}

class CustomFormsLinkModel(object):
    # Dummy class to identify linked models with
    pass

class CustomFormsCache:
    """
    Holds a global cache of all models and fields available to customforms.
    Uses the Borg design pattern like Django's AppCache class.
    """

    __shared_state = dict(
        only_fkey_models={},
        link_fields={},
        loaded=False,
    )

    def __init__(self):
        self.__dict__ = self.__shared_state

    def _populate(self):
        """
        Populates the cache with metadata about models
        """
        if self.loaded:
            return

        for model in apps.get_models():
            if CustomFormsLinkModel in model.__bases__:
                if not hasattr(model, 'link_fields_list'):
                    # only_fkey model
                    self.only_fkey_models.update({model.form_link_name : model})
                else:
                    # This model has linked fields
                    self.link_fields[model.form_link_name] = {'model': model, 'fields': {}}
                    # Now getting the fields
                    all_form_fields = fields_for_model(model, widgets = getattr(model, 'link_fields_widgets', None))
                    sublist = getattr(model, 'link_fields_list')
                    for field, display_name in sublist:
                        field_name = model.__name__ + "_" + field

                        if field in all_form_fields:
                            field_instance = all_form_fields[field]
                            generic_field_type = self.getGenericType(field_instance)
                        else:
                            field_instance = self.getCustomFieldInstance(field, '%s_%s' % (model.form_link_name, field))
                            generic_field_type = 'custom'

                        model_field = field
                        if hasattr(model, 'link_compound_fields') and field_name in model.link_compound_fields:
                            model_field = model.link_compound_fields[field_name]

                        self.link_fields[model.form_link_name]['fields'].update({ field_name: {
                            'model_field': field,
                            'disp_name': display_name,
                            'field_type': generic_field_type,
                            'ques': field_instance.label, # default label
                            'required': field_instance.required,
                        }
                        })

        self.loaded = True

    def getGenericType(self, field_instance):
        """
        Returns the generic field type (e.g. textField) corresponding to this widget.
        This information is useful for rendering this field in the form builder, and for
        setting classes on link fields when they are rendered in the form.
        If this field doesn't resemble any of the generic fields, we return 'custom'.
        We first try to match the field class and widget. If there's no match, we just
        try to macth the widget.
        """
        widget = field_instance.widget
        for k,v in generic_fields.items():
            # First, try and match the field class and corresponding widget
            if field_instance.__class__ is v['typeMap']:
                if widget.__class__ is v['attrs']['widget']:
                    return k

        # Now try to match widgets. Only useful for rendering in the form builder.
        # Check -> does this break for any case? We'll get the wrong classes matched up
        # with the wrong field, and correspondingly the wrong client-side validation.
        backup_type = 'custom'
        for k,v in generic_fields.items():
            if widget is v['attrs']['widget'] or (widget.__class__ is v['attrs']['widget']):
                return k
            try:
                if v['attrs']['widget'] in widget.__bases__:
                    return k
            except AttributeError:
                if v['attrs']['widget'] in widget.__class__.__bases__:
                    backup_type = k

        #   Hm, maybe we should actually check if a custom field has been defined here.
        return backup_type

    def getCustomFieldInstance(self, field, field_name):
        if field in custom_fields:
            field_class = custom_fields[field][0]
            args = custom_fields[field][1]
            kwargs = custom_fields[field][2]
            if field_name or 'name' not in kwargs:
                kwargs['name'] = field_name
            return field_class(*args, **kwargs)
        else:
            raise Exception('Cannot understand field type: %s' % field)

    def isLinkField(self, field):
        """
        Convenience method to get check if 'field' is a link field
        """
        if field not in generic_fields: return True
        else: return False

    def isCompoundLinkField(self, model, field):
        if hasattr(model, 'link_compound_fields') and field in model.link_compound_fields:
            return True
        else:
            return False

    def getCompoundLinkFields(self, model, field):
        if hasattr(model, 'link_compound_fields') and field in model.link_compound_fields:
            return model.link_compound_fields[field]
        else:
            raise Exception('%s is not a compound field on %s' % (field, model))

    def getLinkFieldData(self, field):
        """
        Convenience method to get data for a particular linked field
        """
        for category, options in self.link_fields.items():
            if field in options['fields']: return options['fields'][field]

    def modelForLinkField(self, field):
        """
        Returns the model associated with a particular link field.
        """
        for category, options in self.link_fields.items():
            if field in options['fields']: return options['model']

cf_cache = CustomFormsCache()

