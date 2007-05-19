from django import oldforms
from django.template.defaultfilters import addslashes
from django.contrib.auth.models import User
import re

get_id_re = re.compile('\D*(\d+)\D$')

class AjaxForeignKeyFormField(oldforms.FormField):
    def __init__(self, field_name, field,
                 is_required=False, validator_list=None,
                 member_name=None, ajax_func = None, width=None):

        self.field_name  = field_name
        self.field       = field
        self.is_required = is_required

        if width is None:
            self.width = '25em'
        else:
            self.width = width

        if ajax_func is None:
            self.ajax_func = 'ajax_autocomplete'
        else:
            self.ajax_func = ajax_func
        
        if validator_list is None:
            validator_list = []

        self.validator_list = validator_list

    def extract_data(self, data):
        return data.get(self.field.attname, '')


    def render(self, data):
        """
        Renders the actual ajax widget.
        """

        init_val = data

        if data:
            objects = self.field.rel.to.objects.filter(pk = data)
            if objects.count() == 1:
                obj = objects[0]
                if hasattr(obj, 'ajax_str'):
                    init_val = obj.ajax_str() + " (%s)" % data
                else:
                    init_val = obj.__str__() + " (%s)" % data
        else:
            data = init_val = ''


        fn = self.field_name
        related_model = self.field.rel.to
        # espuser hack
        if related_model == User:
            model_module = 'esp.users.models'
            model_name   = 'ESPUser'
        else:
            model_module = related_model.__module__
            model_name   = related_model.__name__
        
        javascript = """
<script type="text/javascript">
<!--

document.getElementById("id_%s").value = "%s";

var %s_data = new YAHOO.widget.DS_XHR("/admin/ajax_autocomplete/",
                                      ['result','ajax_str','id']);

%s_data.scriptQueryParam  = "ajax_data";
%s_data.scriptQueryAppend = "model_module=%s&model_name=%s&ajax_func=%s";
%s_data.connTimeout = 3000;

var autocomp__%s = new YAHOO.widget.AutoComplete("id_%s","id_%s__container",%s_data);

autocomp__%s.allowBrowserAutocomplete = false;
//autocomp__%s.typeAhead = true;
autocomp__%s.animVert = true;
autocomp__%s.queryDelay = .2;
autocomp__%s.maxCacheEntries = 60; 
autocomp__%s.animSpeed = .5;
autocomp__%s.useShadow = true;
autocomp__%s.useIFrame = true;


YAHOO.util.Event.addListener(window, "load", function (e) {
  var elements = YAHOO.util.Dom.getElementsByClassName('add-another', 'a');
  for (var i=0; i<elements.length; i++) {
    elements[i].style.display = 'none';
  }
  var elements = YAHOO.util.Dom.getElementsByClassName('form-row', 'div');
  for (var i=0; i< elements.length; i++) {
    elements[i].style.overflow = 'visible';
    if (YAHOO.util.Dom.getElementsByClassName('yui_autocomplete','div', elements[i]).length > 0) {
        elements[i].style.paddingBottom = '12.5em';
    }
  }
});

//-->
</script>""" % \
         (fn, addslashes(init_val),
          fn, fn, fn, model_module, model_name, self.ajax_func,
          fn, fn, fn, fn, fn, fn, fn, fn, fn, fn, fn, fn, fn)

        css = """
<style type="text/css">
    /* Taken from Yahoo... */
    #id_%s__yui_autocomplete {position:relative;width:%s;margin-bottom:1em;}/* set width of widget here*/
    #id_%s__yui_autocomplete {z-index:0} /* for IE z-index of absolute divs inside relative divs issue */
    #id_%s__yui_autocomplete input {_position:absolute;width:100%%;height:1.4em;z-index:0;} /* abs for ie quirks */
    #id_%s__container {position:relative; width:100%%;}
    #id_%s__container .yui-ac-content {position:absolute;width:100%%;border:1px solid #ccc;background:#fff;overflow:hidden;z-index:9050;}
    #id_%s__container .yui-ac-shadow {position:absolute;margin:.3em;width:100%%;background:#eee;z-index:8000;}
    #id_%s__container ul {padding:5px 0;width:100%%; list-item-type: none;margin-left: 0; padding-left: 0;z-index:9000;}
    #id_%s__container li {padding:0 5px;cursor:default;white-space:nowrap;padding-left: 0; margin-left: 0;}
    #id_%s__container li.yui-ac-highlight {background:#9cf;z-index:9000;}
    #id_%s__container li.yui-ac-prehighlight {background:#CCFFFF;z-index:9000;}
    .yui-ac-bd { padding:0; margin: 0; z-index:9000;}
</style>
""" % \
        (fn,self.width,fn,fn,fn,fn,fn,fn,fn,fn,fn)

        html = """
<div class="container" style="position: relative;">
<div class="yui_autocomplete" id="id_%s__yui_autocomplete">
  <input type="text" id="id_%s" name="%s" class="vCharField" value="%s" />
  <div id="id_%s__container" class="yui_container"></div>
</div>
</div>
""" % (fn,fn,fn,addslashes(init_val),fn)

        return css + html + javascript

    def prepare(self, new_data):
        id = new_data.get(self.field_name, None)
        if id:
            try:
                id = int(id)
            except ValueError:
                match = get_id_re.match(id)
                id = match.groups()[0]
        new_data[self.field_name] = id
