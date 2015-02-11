import re
import os

from django.db import models
from south.db import db
from django.db.models.loading import cache
from django.db import transaction
from esp.customforms.models import Field
from esp.cache import cache_function
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
        -Uses South for db operations
        - __init__() takes as input two arguments -> 'form', the current Form instance, and 'fields', 
            a list of (field_id, field_type) tuples
        -'fields' is optional. If not provided, it is computed automatically.    
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
        'boolean': {'typeMap': models.BooleanField, 'attrs':{}, 'args':[]},
        'null_boolean': {'typeMap': models.NullBooleanField, 'attrs':{}, 'args':[]},
        'instructions': {'typeMap': None},
    }
    
    
    def __init__(self, form, fields=[]):
        self.form = form
        self.field_list = []
        self.fields = fields
        self._tname = 'customforms\".\"customforms_response_%d' % form.id
        self.link_models_list = []     # Used to store the names of models that are currently linked to via link fields
    
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
            self.field_list.append( ('user', models.ForeignKey(ESPUser, null = True, blank = True, on_delete = models.SET_NULL) ) )
            
        # Checking for only_fkey links
        if self.form.link_type != '-1':
            model_cls = cf_cache.only_fkey_models[self.form.link_type]
            self.field_list.append( ('link_%s' % model_cls.__name__, models.ForeignKey(model_cls, null=True, blank=True, on_delete=models.SET_NULL)) )
            
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
        
        # Adding foreign key fields for link-field models
        for model in link_models:
            if model:
                self.field_list.append( ('link_%s' % model.__name__, models.ForeignKey(model, null=True, blank=True, on_delete=models.SET_NULL) ) )
                self.link_models_list.append(model.__name__)
                    
        return self.field_list
        
    def createTable(self):
        """
        Sets up the database table using self.field_list
        """
        
        if not self.field_list:
            self._getModelFieldList()
        
        if not transaction.is_managed():
            db.start_transaction()
            db.create_table(self._tname, tuple(self.field_list))
            
            # Executing deferred SQL, after correcting the CREATE INDEX statements
            deferred_sql = []
            for stmt in db.deferred_sql:
                deferred_sql.append(re.sub('^CREATE INDEX \"customforms\".', 'CREATE INDEX ', stmt))
            db.deferred_sql = deferred_sql    
            db.execute_deferred_sql()    
            db.commit_transaction()
        else:
            db.create_table(self._tname, tuple(self.field_list))
            
            # Executing deferred SQL, after correcting the CREATE INDEX statements
            deferred_sql = []
            for stmt in db.deferred_sql:
                deferred_sql.append(re.sub('^CREATE INDEX \"customforms\".', 'CREATE INDEX ', stmt))
            db.deferred_sql = deferred_sql    
            db.execute_deferred_sql()    
        
    def deleteTable(self):
        """
        Deletes the response table for the current form
        """
        db.start_transaction()
        db.delete_table(self._tname)
        db.commit_transaction()
        
    def _getFieldToAdd(self, ftype):
        """
        Returns the model field to add, along with a suitable default
        """
        attrs = self._field_types[ftype]['attrs'].copy()
        args = self._field_types[ftype]['args']
        if ftype != "numeric":
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
    
    def addOrUpdateField(self, field, db_func, **kwargs):
        """
        Applies db_func to a column (or columns) corresponding to a particular field
        Depending on db_func, this can be used to ADD COLUMN or ALTER COLUMN
        """
        field_name = self.get_field_name(field)
        #   TODO: Return early if this is a linked field
        db_func(self._tname, field_name, self._getFieldToAdd(field.field_type), **kwargs)
        
    def addField(self, field):
        self.addOrUpdateField(field, db.add_column, keep_default=False)

    def updateField(self, field):
        self.addOrUpdateField(field, db.alter_column)
        
    def removeField(self, field):
        """
        Removes a column (or columns) corresponding to a particular field
        """
        field_name = self.get_field_name(field)
        #   TODO: Return early if this is a linked field
        db.delete_column(self._tname, field_name)
        
    def removeLinkField(self, field):
        """
        Removes the FK-column corresponding to a link field if present.
        """
        if not cf_cache.isLinkField(field.field_type):
            return
        model_cls = cf_cache.modelForLinkField(field.field_type)
        if model_cls.__name__ in self.link_models_list:
            field_name = 'link_%s' % model_cls.__name__
            db.delete_column(self._tname, "%s_id" % field_name)
            self.link_models_list.remove(model_cls.__name__)
        
    def addLinkFieldColumn(self, field):
        """
        Checks if the FK-column corresponding to this link field is already present.
        If not, it adds in the column.
        """
        if not cf_cache.isLinkField(field.field_type):
            return    
        model_cls = cf_cache.modelForLinkField(field.field_type)
        if model_cls.__name__ not in self.link_models_list:
            # Add in the FK-column for this model
            field_name = self.get_field_name(field)
            db.add_column(self._tname, field_name, models.ForeignKey(model_cls, null=True, blank=True, on_delete=models.SET_NULL))
            self.link_models_list.append(model_cls.__name__)
        
    def change_only_fkey(self, old_link_type, new_link_type):
        """
        Used to change the foreign key corresponding to only_fkey_links when a 
        form is modified.
        """
        
        if old_link_type != new_link_type and old_link_type != "-1":
            # Old FK column needs to go
            old_model_cls = cf_cache.only_fkey_models[old_link_type]
            old_field_name = 'link_%s' % old_model_cls.__name__
            db.delete_column(self._tname, "%s_id" % old_field_name)
            
        if old_link_type != new_link_type and new_link_type != "-1":
            # New FK column needs to be inserted
            new_model_cls = cf_cache.only_fkey_models[new_link_type]
            new_field_name = 'link_%s' % new_model_cls.__name__
            db.add_column(self._tname, new_field_name, models.ForeignKey(new_model_cls, null=True, blank=True, on_delete=models.SET_NULL))
    
    def createDynModel(self):
        """
        Creates and returns the dynamic model for this form
        """
        
        _db_table = self._tname
        _model_name = 'Response_%d' % self.form.id
        
        # Removing any existing model definitions from Django's cache
        try:
            del cache.app_models[self._app_label][_model_name.lower()]
        except KeyError:
            pass
            
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
                
        
# Giving it an alias that's less of a mouthful        
DMH = DynamicModelHandler

