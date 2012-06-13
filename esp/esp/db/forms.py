from django.db import models
from django import forms
from django.template.defaultfilters import addslashes
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
import re

get_id_re = re.compile('.*\D(\d+)\D')

class AjaxForeignKeyFieldBase:

    def render(self, *args, **kwargs):
        """
        Renders the actual ajax widget.
        """            
        if len(args) == 1:
            data = args[0]
        else:
            data = args[1]

        old_init_val = init_val = data

        if type(data) == int:
            if hasattr(self, "field"):
                query_objects = self.field.rel.to.objects
                
            objects = query_objects.filter(pk = data)
            if objects.count() == 1:
                obj = objects[0]
                if hasattr(obj, 'ajax_str'):
                    init_val = obj.ajax_str() + " (%s)" % data
                    old_init_val = unicode(obj)
                else:
                    old_init_val = init_val = unicode(obj) + " (%s)" % data
        elif isinstance(data, str) or isinstance(data, unicode):
            pass
        else:
            data = init_val = ''

        fn = str(self.field_name)
        
        related_model = self.field.rel.to
        # espuser hack
        if related_model == User:
            model_module = 'esp.users.models'
            model_name   = 'ESPUser'
        else:
            model_module = related_model.__module__
            model_name   = related_model.__name__

        if self.shadow_field:
            shadow_field_javascript = """
                $j("#id_%s").val(ui.item.value);
            """ % (self.shadow_field)
        else:
            shadow_field_javascript = ""
        
        javascript = """
<script type="text/javascript">
<!--

$j("#id_%s").val("%s");
$j("#id_%s").autocomplete({
    source: function(request, response) {
        $j.ajax({
            url: "/admin/ajax_autocomplete/",
            dataType: "json",
            data: {
                model_module: "%s",
                model_name: "%s",
                ajax_func: "%s",
                ajax_data: request.term
            },
            success: function(data) {
                var output = $j.map(data.result, function(item) {
                    return {
                        label: item.ajax_str,
                        value: item.ajax_str,
                        id: item.id,
                    };
                });
                response(output);
            }
        });
    },
    select: function(event, ui) {
        $j("#id_%s_data").val(ui.item.id);
        %s
    }
});


//-->
</script>""" % \
         (fn, addslashes(init_val), fn,
          model_module, model_name, self.ajax_func or 'ajax_autocomplete',
          fn, shadow_field_javascript)

        html = """
<input type="text" id="id_%s" name="%s_raw" value="%s" />
<input type="hidden" id="id_%s_data" name="%s" />
<div class="raw_id_admin">
  <a href="../" class="related-lookup" id="lookup_%s" onclick="return showRelatedObjectLookupPopup(this);">
  <img src="/media/admin/img/admin/selector-search.gif" border="0" width="16" height="16" alt="Lookup" /></a>   
   &nbsp;<strong>%s</strong>
</div>
""" % (fn,fn,addslashes(data or ''),fn,fn,fn,old_init_val)
       
        #   Add HTML for shadow field if desired
        if self.shadow_field:
            html += '<input type="hidden" id="id_%s" name="%s" value="%s"/>' % (self.shadow_field, self.shadow_field, old_init_val)

        return mark_safe(html + javascript)
    
class AjaxForeignKeyWidget(AjaxForeignKeyFieldBase, forms.widgets.Widget):
    choices = ()
    
    def __init__(self, attrs=None, *args, **kwargs):    
        super(AjaxForeignKeyWidget, self).__init__(attrs, *args, **kwargs)

        if attrs.has_key('field'):
            self.field = attrs['field']
        elif attrs.has_key('type'):
            #   Anyone have a better hack here?
            self.field = models.ForeignKey(attrs['type'])

        self.field_name = self.field.name

        if attrs.has_key('width'):
            self.width = attrs['width']

        if attrs.has_key('ajax_func'):
            self.ajax_func = attrs["ajax_func"]
            
        if attrs.has_key('shadow_field'):
            self.shadow_field = attrs['shadow_field']
        else:
            self.shadow_field = None

        if attrs.has_key('field_name'):
            self.field_name = attrs['field_name']
            self.field.name = attrs['field_name']

    #   render function is provided by AjaxForeignKeyFieldBase    
    
class AjaxForeignKeyNewformField(forms.IntegerField):
    """ An Ajax autocompletion field that works like the other fields in django.forms.
        You need to initialize it in one of two ways:
        -   [name] = AjaxForeignKeyNewformField(key_type=[model], field_name=[name])
        -   [name] = AjaxForeignKeyNewformField(field=[field])
            where [field] is the field in a model (i.e. ForeignKey) 
    """
    def __init__(self, field_name='', field=None, key_type=None, to_field=None,
                 to_field_name=None, required=True, label='', localize=False, initial=None,
                 widget=None, help_text='', ajax_func=None, queryset=None,
                 error_messages=None, show_hidden_initial=False, shadow_field_name=None,
                 *args, **kwargs):

        if ajax_func is None:
            self.widget.ajax_func = 'ajax_autocomplete'
        else:
            self.widget.ajax_func = ajax_func
        
        self.localize = localize
        
        # ---
        # We don't do anything with these arguments, but maybe we should.
        # As of now we just assume we're looking for the id. -ageng 2008-12-22
        if to_field_name is None:
            to_field_name = 'id'
        if to_field_name != 'id':
            raise NotImplementedException
        if to_field is not None:
            raise NotImplementedException
        self.show_hidden_initial = show_hidden_initial
        # ---
        
        if field:
            self.widget = AjaxForeignKeyWidget(attrs={'field': field, 'width': 35, 'ajax_func': ajax_func, 'shadow_field': shadow_field_name})
        elif key_type:
            self.widget = AjaxForeignKeyWidget(attrs={'type': key_type, 'width': 35, 'ajax_func': ajax_func, 'shadow_field': shadow_field_name, 'field_name': field_name})
            self.key_type = key_type
        else:
            raise NotImplementedError

        if isinstance(self.widget, type):
            self.widget = self.widget()

        extra_attrs = self.widget_attrs(widget)
        if extra_attrs:
            widget.attrs.update(extra_attrs)

        self.creation_counter = forms.Field.creation_counter
        forms.Field.creation_counter += 1                                                        
        
        self.required = required
        self.help_text = help_text
        self.initial = initial
        if field_name != '':
            self.widget.field_name = field_name
        if label == '':
            self.label = field_name
        else:
            self.label = label
        if field is not None: # Note: DO NOT use "!=" here!  It will get translated to field.__cmp__(None); field.__cmp__ assumes that its only argument is another field.
            self.set_field(field)
            
    def set_field(self, field):
        self.field = field
        self.widget.field = field
            
    def clean(self, value):
        if (value is None or value == '') and not self.required:
            return None
        
        try:
            id = int(value)
        except ValueError:
            match = get_id_re.match(value)
            if match:
                id = int(match.groups()[0])
            else:
                #   Reverted to standard behavior because some forms need their
                #   AjaxForeignKey fields to be required.  -Michael P 8/31/2009
                if self.required:
                    raise forms.ValidationError('This field is required.')
                else:
                    id = None
                

        if hasattr(self, "field"):
            # If we couldn't grab an ID, ask the target's autocompleter.
            if id == None:
                objs = self.field.rel.to.ajax_autocomplete(value)
                if len( objs ) == 1:
                    id = objs[0]['id']
            # Finally, grab the object.
            if id:
                return self.field.rel.to.objects.get(id=id)

        elif hasattr(self, 'key_type') and id is not None:
            return self.key_type.objects.get(id=id)

        return id
