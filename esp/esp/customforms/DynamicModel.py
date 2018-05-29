import re
import os

from django.db import models
from django.apps import apps
from django.db import connection, transaction
from esp.customforms.models import Field
from argcache import cache_function
from esp.users.models import ESPUser
from esp.program.models import ClassSubject
from esp.customforms.linkfields import cf_cache
from esp.qsdmedia.models import root_file_path
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

def get_file_upload_path(instance, filename):
    """
    Returns the upload path for the file that is to be saved.
    Files are saved in the directory MEDIA_ROOT/uploaded/Response_[form_id]
    """
    save_dir = 'uploaded/%s' % instance.__class__.__name__
    save_dir = os.path.join(settings.MEDIA_ROOT, save_dir)
    save_path = os.path.join(save_dir, filename)
    return save_path

class DynamicModelHandler:
    """
    Handler class for creating, modifying and deleting dynamic models
        -Uses Django's SchemaEditor API for db operations
        - __init__() takes as input two arguments -> 'form', the current Form instance, and 'fields',
            a list of (field_id, field_type) tuples
        -'fields' is optional. If not provided, it is computed automatically.

    -----

    I'm not the original author of the code, I'm just updating it, and I'm not entirely sure
    that the following is correct, but I want to leave these notes for the next person to
    have to modify this:

    You might look at this, notice that there's some weird special handling of foreign keys
    going on, and wonder what it's there for. Here's my best guess at what it's doing.

    - The one called "only_fkey" or "link_type" is the custom form's link. A custom form can
    be associated with a particular model, usually a program. As far as I can tell this doesn't
    do anything, but it's there and it's in use.

    - If the form is not anonymous, it'll need a foreign key to ESPUser.

    - Then there are other "link fields". This is the weird one. I think the idea is that you
    can have a custom form with fields that are actually stored in another model. The custom form
    responses table has a foreign key to that other model. The form will have multiple fields
    that are part of this linked model, and you might add or remove one of those, but the existence
    of the foreign key in the custom forms table shouldn't change unles you've added a new one
    or removed all of them. This is why you have to keep track of them and check, and have
    separate add and remove methods from the normal fields.
    """

    _app_label = 'customforms'
    _module = 'esp.customforms.models'
    _schema_name = 'customforms'

    _field_types = {
        'textField': {'typeMap': models.CharField, 'attrs': {'max_length': 30,}, 'args': []},
        'longTextField': {'typeMap': models.CharField, 'attrs': {'max_length': 60,}, 'args': []},
        'longAns': {'typeMap': models.TextField, 'attrs': {}, 'args': []},
        'reallyLongAns': {'typeMap': models.TextField, 'attrs': {}, 'args': []},
        'radio': {'typeMap': models.CharField, 'attrs': {'max_length': 200,}, 'args': []},
        'dropdown': {'typeMap': models.CharField, 'attrs': {'max_length': 200,}, 'args': []},
        'multiselect': {'typeMap': models.TextField, 'attrs': {}, 'args': []},
        'checkboxes': {'typeMap': models.TextField, 'attrs': {}, 'args': []},
        'numeric': {'typeMap': models.IntegerField, 'attrs': {'null': True, }, 'args': []},
        'date': {'typeMap': models.CharField, 'attrs': {'max_length': 10, }, 'args': []},
        'time': {'typeMap': models.CharField, 'attrs': {'max_length': 10, }, 'args': []},
        'file': {'typeMap': models.FileField, 'attrs': {'max_length': 200, 'upload_to': get_file_upload_path, }, 'args': []},
        'phone': {'typeMap': models.CharField, 'attrs': {'max_length': 15}, 'args': []},
        'email': {'typeMap': models.CharField, 'attrs': {'max_length': 30,}, 'args':[]},
        'state': {'typeMap': models.CharField, 'attrs': {'max_length': 2}, 'args': []},
        'gender': {'typeMap': models.CharField, 'attrs': {'max_length': 2}, 'args': []},
        'radio_yesno': {'typeMap': models.CharField, 'attrs':{'max_length': 1,}, 'args':[]},
        'boolean': {'typeMap': models.BooleanField, 'attrs':{'default': False}, 'args':[]},
        'null_boolean': {'typeMap': models.NullBooleanField, 'attrs':{}, 'args':[]},
        'instructions': {'typeMap': None},
    }


    def __init__(self, form, fields=[]):
        self.form = form
        self.field_list = []
        self.fields = fields
        self._tname = 'customforms\".\"customforms_response_%d' % form.id
        # Keep track of the models being linked to (see docstring)
        self.link_models_list = []

    def __marinade__(self):
        """
        Implemented for caching convenience
        """
        return 'dyn'

    # CHECK THIS
    @cache_function
    def _getFieldsForForm(self, form):
        """
        Gets the list of (field_id, field_type) tuples for the present form.
        Called if this list isn't passed to __init__() and the dynamic model needs to be generated.
        """
        self.fields = Field.objects.filter(form=form).values_list('id', 'field_type')
        return self.fields
    _getFieldsForForm.depend_on_row('customforms.Field', lambda field: {'form': field.form})

    def _getModelField(self, field_type):
        """
        Returns the appropriate Django Model Field based on field_type
        """
        if self._field_types[field_type]['typeMap']:
            return self._field_types[field_type]['typeMap'](*self._field_types[field_type]['args'], **self._field_types[field_type]['attrs'])
        else:
            return None

    def _getLinkModelField(self, model):
        """
        Returns a ForeignKey Field for the given model
        """
        # If I don't set db_index=False here, Django tries to create an index,
        # which breaks because Django doesn't know that customforms is in its
        # own schema
        return models.ForeignKey(model, null=True, blank=True, on_delete=models.SET_NULL, db_index=False)

    def _getModelFieldList(self):
        """
        Returns a list of Model Field tuples given a list of field_types (from the metadata)
            - An entry would be like (field_name, field)
            - An 'id' field is automatically added, as is a 'user_id' field, based on whether the form
              is anonymous or not.
            - A field-name is of the form 'question_23', where '23' is the ID of the corresponding question
            - For custom fields like address, a field-name would be of the form 'question_23_zip'
        """
        link_models = []
        if not self.fields:
            self.fields = self._getFieldsForForm(self.form)

        self.field_list.append( ('id', models.AutoField(primary_key = True) ) )
        if not self.form.anonymous:
            self.field_list.append( ('user', self._getLinkModelField(ESPUser) ) )

        # Checking for only_fkey links
        if self.form.link_type != '-1':
            model_cls = cf_cache.only_fkey_models[self.form.link_type]
            self.field_list.append( ('link_%s' % model_cls.__name__, self._getLinkModelField(model_cls)) )

        # Check for linked fields-
        # Insert a foreign-key to the parent model for link fields
        # Insert a regular column for non-link fields
        for field_id, field in self.fields:
            if cf_cache.isLinkField(field):
                lm = cf_cache.modelForLinkField(field)
                if lm not in link_models: link_models.append(lm)
            else:
                new_field = self._getModelField(field)
                if new_field:
                    self.field_list.append( ('question_%s' % str(field_id), new_field) )

        for model in link_models:
            if model:
                new_field = self._getLinkModelField(model)
                self.field_list.append( ('link_%s' % model.__name__, new_field) )
                self.link_models_list.append(model.__name__)

        return self.field_list

    def createTable(self):
        """
        Sets up the database table using self.field_list
        """

        if not self.field_list:
            self._getModelFieldList()

        if transaction.get_autocommit():
            with transaction.atomic():
                with connection.schema_editor() as schema_editor:
                    schema_editor.create_model(self.createDynModel())
        else:
            with connection.schema_editor() as schema_editor:
                schema_editor.create_model(self.createDynModel())

    @transaction.atomic
    def deleteTable(self):
        """
        Deletes the response table for the current form
        """
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(self.createDynModel())
        self.purgeDynModel()

    def _getFieldToAdd(self, ftype):
        """
        Returns the model field to add, along with a suitable default
        """
        attrs = self._field_types[ftype]['attrs'].copy()
        args = self._field_types[ftype]['args']
        if ftype != "numeric" and ftype  != "boolean":
            attrs['default'] = ''
        return self._field_types[ftype]['typeMap'](*args, **attrs)

    def get_field_name(self, field):
        """
        Returns the field name for this field.
        Returns the field name corresponding to the linked model for link fields.
        """
        if cf_cache.isLinkField(field.field_type):
            model = cf_cache.modelForLinkField(field.field_type)
            return 'link_'+model.__name__

        return "question_%d" % field.id

    def addField(self, field):
        with connection.schema_editor() as schema_editor:
            model = self.createDynModel()
            field_name = self.get_field_name(field)
            schema_editor.add_field(model, model._meta.get_field(field_name))

    def updateField(self, field, old_field):
        with connection.schema_editor() as schema_editor:
            model = self.createDynModel()
            field_name = self.get_field_name(field)
            schema_editor.alter_field(model, self._getModelField(old_field),
                                      model._meta.get_field(field_name))

    def removeField(self, field):
        """
        Removes a column (or columns) corresponding to a particular field
        """
        with connection.schema_editor() as schema_editor:
            model = self.createDynModel()
            field_name = self.get_field_name(field)
            #   TODO: Return early if this is a linked field
            schema_editor.remove_field(model, model._meta.get_field(field_name))

    def removeLinkField(self, field):
        """
        Removes the FK-column corresponding to a link field if present.
        """
        if not cf_cache.isLinkField(field.field_type):
            return
        with connection.schema_editor() as schema_editor:
            model = self.createDynModel()
            link_model_cls = cf_cache.modelForLinkField(field.field_type)
            if link_model_cls.__name__ in self.link_models_list:
                field_name = 'link_%s' % link_model_cls.__name__
                schema_editor.remove_field(model, model._meta.get_field(field_name))
                self.link_models_list.remove(link_model_cls.__name__)

    def addLinkFieldColumn(self, field):
        """
        Checks if the FK-column corresponding to this link field is already present.
        If not, it adds in the column.
        """
        if not cf_cache.isLinkField(field.field_type):
            return
        with connection.schema_editor() as schema_editor:
            link_model_cls = cf_cache.modelForLinkField(field.field_type)
            if link_model_cls.__name__ not in self.link_models_list:
                # Add in the FK-column for this model
                model = self.createDynModel()
                field_name = self.get_field_name(field)
                schema_editor.add_field(model, model._meta.get_field(field_name))
                self.link_models_list.append(link_model_cls.__name__)

    def change_only_fkey(self, form, old_link_type, new_link_type, link_id):
        """
        Used to change the foreign key corresponding to only_fkey_links when a
        form is modified.
        """
        with connection.schema_editor() as schema_editor:
            if old_link_type != new_link_type and old_link_type != "-1":
                # Old FK column needs to go
                model = self.createDynModel()
                old_model_cls = cf_cache.only_fkey_models[old_link_type]
                old_field_name = 'link_%s' % old_model_cls.__name__
                schema_editor.remove_field(model, model._meta.get_field(old_field_name))

            form.link_type = new_link_type
            form.link_id = link_id
            form.save()

            if old_link_type != new_link_type and new_link_type != "-1":
                # New FK column needs to be inserted
                model = self.createDynModel()
                new_model_cls = cf_cache.only_fkey_models[new_link_type]
                new_field_name = 'link_%s' % new_model_cls.__name__
                schema_editor.add_field(model, model._meta.get_field(new_field_name))

    def createDynModel(self):
        """
        Creates and returns the dynamic model for this form
        """

        _db_table = self._tname
        _model_name = 'Response_%d' % self.form.id

        # Removing any existing model definitions from Django's cache
        self.purgeDynModel()

        class Meta:
            app_label = self._app_label
            db_table = _db_table

        attrs = {'__module__': self._module, 'Meta': Meta}

        # Updating attrs with the fields
        if not self.field_list:
            self._getModelFieldList()
        attrs.update(dict(self.field_list))

        dynModel = type(_model_name, (models.Model,), attrs)
        return dynModel

    def purgeDynModel(self):
        """
        Purges the model from Django's app registry cache.
        """

        _model_name = 'Response_%d' % self.form.id
        try:
            # TODO: private API, please fix
            del apps.get_app_config(self._app_label).models[_model_name.lower()]
            apps.clear_cache()
        except KeyError:
            pass


# Giving it an alias that's less of a mouthful
DMH = DynamicModelHandler

