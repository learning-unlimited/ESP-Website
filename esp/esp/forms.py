from django import forms

class SizedCharField(forms.CharField):
    """ Just like CharField, but you can set the width of the text widget. """
    def __init__(self, length=None, *args, **kwargs):
        forms.CharField.__init__(self, *args, **kwargs)
        self.widget.attrs['size'] = length

class BlankSelectWidget(forms.Select):
    """ A <select> widget whose first entry is blank. """
    
    def __init__(self, blank_choice=('',''), *args, **kwargs):
        super(forms.Select, self).__init__(*args, **kwargs)
        self.blank_value = blank_choice[0]
        self.blank_label = blank_choice[1]
    
    # Copied from django/forms/widgets.py
    def render(self, name, value, attrs=None, choices=()):
        from django.utils.html import escape, conditional_escape
        from django.utils.encoding import force_unicode
        from django.utils.safestring import mark_safe
        
        if value is None: value = ''
        final_attrs = self.build_attrs(attrs, name=name)
        output = [u'<select%s>' % forms.util.flatatt(final_attrs)]
        output.append( u'<option value="%s" selected="selected">%s</option>' %
                       (escape(self.blank_value), conditional_escape(force_unicode(self.blank_label))) )
        options = self.render_options(choices, [value])
        if options:
            output.append(options)
        output.append('</select>')
        return mark_safe(u'\n'.join(output))
    

# TODO: Make this not suck
class SplitDateWidget(forms.MultiWidget):
    """ A date widget that separates days, etc. """

    def __init__(self, attrs=None):
        from datetime import datetime

        year_choices = range(datetime.now().year - 70,
                             datetime.now().year - 10)
        year_choices.reverse()
        month_choices = ['%02d' % x for x in range(1, 13)]
        day_choices   = ['%02d' % x for x in range(1, 32)]
        choices = {'year' : [('',' ')] + zip(year_choices, year_choices),
                   'month': [('',' ')] + zip(range(1, 13), month_choices),
                   'day'  : [('',' ')] + zip(range(1, 32), day_choices)
                   }

        year_widget = forms.Select(choices=choices['year'])
        month_widget = forms.Select(choices=choices['month'])
        day_widget = forms.Select(choices=choices['day'])

        widgets = (month_widget, day_widget, year_widget)
        super(SplitDateWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        """ Splits datetime.date object into separate fields. """
        if value:
            return [value.month, value.day, value.year]
        return [None, None, None]

    def value_from_datadict(self, data, files, name):
        """ Given a dict, extracts datetime.date object. Appears to require handling of both versions. """
        from datetime import date
        val = data.get(name, None)
        if val is not None:
            return val
        else:
            vals = super(SplitDateWidget, self).value_from_datadict(data, files, name)
            try:
                return date(int(vals[2]), int(vals[0]), int(vals[1]))
            except:
                return None

    # Put labels in
    def format_output(self, rendered_widgets):
        output = u'\n<label for="dob_0">Month:</label>\n'
        output += rendered_widgets[0]
        output += u'\n<label for="dob_1">Day:</label>\n'
        output += rendered_widgets[1]
        output += u'\n<label for="dob_2">Year:</label>\n'
        output += rendered_widgets[2]
        return output


#### NOTE: Python super() does weird things (it's the next in the MRO, not a superclass).
#### DO NOT OMIT IT if overriding __init__() when subclassing these forms

class FormWithRequiredCss(forms.Form):
    """ Form that adds the "required" class to every required widget, to restore oldforms behavior. """
    def __init__(self, *args, **kwargs):
        super(FormWithRequiredCss, self).__init__(*args, **kwargs)
        for field in self.fields.itervalues():
            if field.required:
                field.widget.attrs['class'] = 'required'

class FormUnrestrictedOtherUser(FormWithRequiredCss):
    """ Form that implements makeRequired for the old form --- disables required fields at in some cases. """

    def __init__(self, user=None, *args, **kwargs):
        super(FormUnrestrictedOtherUser, self).__init__(*args, **kwargs)
        if user is None or not (hasattr(user, 'other_user') and user.other_user):
            pass
        else:
            for field in self.fields.itervalues():
                if field.required:
                    field.required = False
                    field.widget.attrs['class'] = None # GAH!

