from django.forms import *
from dataviews import * 
from django.forms.forms import pretty_name, BoundField
from django.core.urlresolvers import get_mod_func
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.utils.html import conditional_escape
from django.utils.encoding import StrAndUnicode, smart_unicode, force_unicode
from django.utils.safestring import mark_safe
from esp.dataviews.forms import *
from django.utils.translation import ugettext_lazy as _

class SplitConditionWidget(widgets.MultiWidget):
    def __init__(self, attrs=None):
        super(SplitConditionWidget, self).__init__((widgets.Select(choices = model_field_choices), widgets.Select(choices = [(query_term, query_term_symbols[query_term]) for query_term in query_terms]), widgets.TextInput), attrs)

    def decompress(self, value): 
        if value and isinstance(value, list):
            return value
        elif value and isinstance(value, basestring):
            return value.split(u'|')
        else:
            return [u'']*3

    def format_output(self, rendered_widgets):
        return u"\n<br />\n<div>\n" + u''.join(rendered_widgets) + u"\n<input type='button' value='Delete' />\n</div>\n<br />\n<hr />\n"

class SplitHiddenConditionWidget(SplitConditionWidget):
    is_hidden = True

    def __init__(self, attrs=None): 
        super(SplitConditionWidget, self).__init__((widgets.HiddenInput, widgets.HiddenInput, widgets.HiddenInput), attrs)
        for widget in self.widgets:
            widget.input_type = 'hidden'
            widget.is_hidden = True
    
    def format_output(self, rendered_widgets):
        return super(SplitConditionWidget, self).format_output(rendered_widgets)

class SplitConditionField(fields.MultiValueField): 
    widget = SplitConditionWidget
    hidden_widget = SplitHiddenConditionWidget
    
    def __init__(self, *args, **kwargs): 
        super(SplitConditionField, self).__init__((ChoiceField(choices = model_field_choices), ChoiceField(choices = [(query_term, query_term_symbols[query_term]) for query_term in query_terms]), CharField()), *args, **kwargs)
    
    def compress(self, data_list): 
        return u'|'.join(data_list)
   
def headingconditionsform_factory(num_conditions = 3): 
    name = "HeadingConditionsForm"
    base = (Form,)
    fields = {'model': ChoiceField(choices=model_choices), 'num_conditions': IntegerField(initial=num_conditions, widget=widgets.HiddenInput)}
    for i in range(num_conditions): 
        fields['condition_'+str(i+1)] = SplitConditionField(initial=[u'', u'exact', u''], required=False)
    return type(name, base, fields)

class SplitColumnFieldWidget(widgets.MultiWidget):
    def __init__(self, attrs=None):
        super(SplitColumnFieldWidget, self).__init__((widgets.Select(choices = model_field_choices), widgets.TextInput), attrs)

    def decompress(self, value): 
        if value and isinstance(value, list):
            return value
        elif value and isinstance(value, basestring):
            return value.split(u'|')
        else:
            return [u'']*2

    def format_output(self, rendered_widgets):
        return u"\n<br />\n<div>\n" + u''.join(rendered_widgets) + u"\n<input type='button' value='Delete' />\n</div>\n<br />\n<hr />\n"

class SplitHiddenColumnFieldWidget(SplitColumnFieldWidget):
    is_hidden = True

    def __init__(self, attrs=None): 
        super(SplitColumnFieldWidget, self).__init__((widgets.HiddenInput, widgets.HiddenInput), attrs)
        for widget in self.widgets:
            widget.input_type = 'hidden'
            widget.is_hidden = True
    
    def format_output(self, rendered_widgets):
        return super(SplitColumnFieldWidget, self).format_output(rendered_widgets)

class SplitColumnFieldField(fields.MultiValueField): 
    widget = SplitColumnFieldWidget
    hidden_widget = SplitHiddenColumnFieldWidget
    
    def __init__(self, *args, **kwargs): 
        super(SplitColumnFieldField, self).__init__((ChoiceField(choices = model_field_choices), CharField()), *args, **kwargs)
    
    def compress(self, data_list): 
        return u'|'.join(data_list)

def displaycolumnsform_factory(num_columns = 3): 
    name = "DisplayColumnsForm"
    base = (Form,)
    fields = {'num_columns': IntegerField(initial=num_columns, widget=widgets.HiddenInput)}
    for i in range(num_columns): 
        fields['field_'+str(i+1)] = SplitColumnFieldField(initial=[u'', u''], required=(not i))
    return type(name, base, fields)

def pathchoiceform_factory(model, all_paths): 
    name = "PathChoiceForm"
    base = (Form,)
    fields = {}
    for I, target_model, model_paths, field in all_paths:
        for (path, models, many) in model_paths: 
            label = unicode(model.__name__)
            if path: 
                for i,n in enumerate(path):
                    label += u' \u2192 ' + pretty_name(n) + u' (' + models[i+1].__name__ + u')'
            label += u' \u2192 ' + pretty_name(unicode(field))
            fields[LOOKUP_SEP.join((str(I)+'|'+target_model.__name__,)+path+(field,))] = BooleanField(required=False, label=label)
    return type(name, base, fields)

class ModeWizard(DataViewsWizard): 
    
    mode = 1
    first_form = headingconditionsform_factory()
    steps = 4
    
    def done(self, request, form_list):
        model = globals()[form_list[0].cleaned_data['model']]
        args = []
        for i in range(self.num_conditions): 
            values = form_list[0].cleaned_data['condition_'+str(i+1)].split(u'|')
            if not values[0]: 
                continue
            condition_model, condition_field = get_mod_func(values[0])
            condition_model = globals()[condition_model]
            query_term = values[1]
            text = values[2]
            val = condition_model._meta.init_name_map()[condition_field][0].to_python(text)
            args.append((condition_model, str(condition_field), str(query_term), val))
        paths = defaultdict(list)
        view_paths = []
        headers = []
        for model_and_path, value in form_list[1].cleaned_data.iteritems():
            if value: 
                _, _, model_and_path = model_and_path.partition('|')
                condition_model, _, path = model_and_path.partition(LOOKUP_SEP)
                path, _, _ = path.rpartition(LOOKUP_SEP)
                paths[globals()[condition_model]].append(path)
        headers = defaultdict(list)
        for model_and_path, value in form_list[3].cleaned_data.iteritems():
            if value: 
                I, _, model_and_path = model_and_path.partition('|')
                _, _, path = model_and_path.partition(LOOKUP_SEP)
                view_paths.append(path)
                headers[int(I)].append(path)
        headers = [[path, form_list[2].cleaned_data['field_'+str(I+1)].split(u'|')[1]] for I in range(self.num_columns) for path in headers[I+1]]
        queryset = path_v5(model, paths, *args).select_related(*view_paths)
        fields = [header[0] for header in headers]
        data = {}
        for field in fields:
            data[field] = list(queryset.values_list('id', field))
        pks = queryset.values_list('pk', flat=True)
        for pk in pks:
            data[pk] = defaultdict(list)
        for field in fields:
            for (pk, datum) in data[field]:
                data[pk][field].append(datum)
        from tempfile import TemporaryFile
        from xlwt import Workbook
        book = Workbook()
        sheet1 = book.add_sheet('Sheet 1')
        field_locations = {}
        for j, header in enumerate(headers):
            sheet1.write(0,j,header[1])
            field_locations[header[0]] = j
        for i, pk in enumerate(pks):
            for field in fields:
                sheet1.write(i+1,field_locations[field], ', '.join(map(str,data[pk][field])))
        response = HttpResponse(mimetype="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename=%s' % 'DataViews.xls'
        book.save(response)
        return response
    
    def parse_params(self, request, *args, **kwargs):
        self.num_conditions = int(request.POST.get('%s-num_conditions' % self.prefix_for_step(0), 3))
        self.num_columns = int(request.POST.get('%s-num_columns' % self.prefix_for_step(2), 3))
        self.form_list[0] = headingconditionsform_factory(self.num_conditions)
        self.form_list[2] = displaycolumnsform_factory(self.num_columns)
    
    def process_step(self, request, form, step): 
        form0 = self.get_form(0, request.POST)
        if not form0.is_valid():
            return self.render_revalidation_failure(request, 0, form0)
        model = globals()[form0.cleaned_data['model']]
        if not step: 
            paths = []
            for i in range(self.num_conditions):
                values = form.cleaned_data['condition_'+str(i+1)].split('|')
                if not values[0]: 
                    continue
                condition_model, condition_field = get_mod_func(values[0])
                condition_model = globals()[condition_model]
                paths.append((i+1, condition_model, path_v1(model, condition_model), condition_field))
            self.form_list[step+1] = pathchoiceform_factory(model, paths)
        elif step == 2:
            paths = []
            for i in range(self.num_columns): 
                values = form.cleaned_data['field_'+str(i+1)].split('|')
                if not values[0]: 
                    continue
                field_model, field_field = get_mod_func(values[0])
                field_model = globals()[field_model]
                paths.append((i+1, field_model, path_v1(model, field_model), field_field))
            self.form_list[step+1] = pathchoiceform_factory(model, paths)
