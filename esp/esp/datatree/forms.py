""" Forms and fields relating to datatrees. """

from esp.datatree.models import DataTree

from django import forms
from django.template import loader

class AjaxTreeSelectorWidget(forms.Widget):
    """ A widget that shows a list of tree names and stores the ID of the selected tree name. """
    def render(self, name, value, attrs={}):
        #   Load HTML from template
        from esp.settings import TEMPLATE_DIRS

        self.attrs.update(attrs)
        
        try:
            initial_node = DataTree.objects.get(id=int(value))
        except:
            initial_node = None
            
        try:            
            root = DataTree.get_by_uri(self.attrs['root_uri'], create=False)
        except:
            root = None
        
        context = {'field_name': name, 'initial_node': initial_node, 'root': root}

        return loader.render_to_string(TEMPLATE_DIRS[0]+'/datatree/tree_select.html', context)

class AjaxTreeField(forms.IntegerField):
    widget = AjaxTreeSelectorWidget
    
    def clean(self, value):
        #   The value should be a valid data tree id.  
        #   If we can't find that tree, we say it's invalid.
        
        super(forms.IntegerField, self).clean(value)
        if value in forms.fields.EMPTY_VALUES:
            return None
        try:
            value = int(str(value))
            node = DataTree.objects.get(id=value)
        except (ValueError, TypeError, DataTree.DoesNotExist):
            raise ValidationError(self.error_messages['invalid'])
        
        return node
    
    def __init__(self, root_uri='', max_depth=None, *args, **kwargs):
        self.root_uri = root_uri
        self.max_depth = max_depth
        super(AjaxTreeField, self).__init__(*args, **kwargs)
        self.widget.attrs['root_uri'] = self.root_uri
