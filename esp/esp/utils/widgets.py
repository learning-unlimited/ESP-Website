#   Downloaded from http://www.djangosnippets.org/snippets/391/
#   Modified to not force unicode
#   - Michael P

from django.conf import settings
from django import newforms as forms
import datetime
import time

# DATETIMEWIDGET
calbtn = u"""<img src="%simages/calbutton.gif" alt="calendar" id="%s_btn" style="cursor: pointer; border: none;" title="Select date and time"
            onmouseover="this.style.background='#444444';" onmouseout="this.style.background=''" />
<script type="text/javascript">
    Calendar.setup({
        inputField     :    "%s",
        ifFormat       :    "%s",
        button         :    "%s_btn",
        singleClick    :    true,
        showsTime      :    true
    });
</script>"""

class DateTimeWidget(forms.widgets.TextInput):
    dformat = '%Y-%m-%d %H:%M'
    
    def render(self, name, value, attrs=None):
        
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        
        if value != '': 
            try:
                final_attrs['value'] = value.strftime(self.dformat)
            except:
                final_attrs['value'] = value
                
        if not final_attrs.has_key('id'):
            final_attrs['id'] = u'%s_id' % (name)
        id = final_attrs['id']
        
        jsdformat = self.dformat #.replace('%', '%%')
        cal = calbtn % (settings.MEDIA_URL, id, id, jsdformat, id)
        a = u'<input%s />%s' % (forms.util.flatatt(final_attrs), cal)
        return a

    def value_from_datadict(self, data, name):
        dtf = forms.fields.DEFAULT_DATETIME_INPUT_FORMATS
        empty_values = forms.fields.EMPTY_VALUES

        value = data.get(name, None)
        if value in empty_values:
            return None
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            return datetime.datetime(value.year, value.month, value.day)
        for format in dtf:
            try:
                return datetime.datetime(*(time.strptime(value, format)[:6]))
            except ValueError:
                continue
        return None