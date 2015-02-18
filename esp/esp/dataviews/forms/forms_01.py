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
from django.db.models.aggregates import * 

def model_field_choices(model, include_Count = False): 
    choices = [(model.__name__+'.id', 'id')]
    if include_Count: 
        choices += [(model.__name__+'.Count', 'Count')]
    choices += sorted([(model.__name__+'.'+fieldname, fieldname) for fieldname, field in model._meta.init_name_map().iteritems() if not (fieldname=='id' or isinstance(field[0], RelatedField) or isinstance(field[0], RelatedObject))], key=lambda choice: choice[0])
    return choices

def all_field_choices(base_model = None, include_Count = False): 
    choices = defaultdict(list)
    for model in useful_models: 
        choices[model] = model_field_choices(model, include_Count = (include_Count and (base_model != model)))
    return [('', "None")]+[(model.__name__, choices[model]) for model in useful_models]

class SplitConditionWidget(widgets.MultiWidget):
    def __init__(self, attrs=None):
        super(SplitConditionWidget, self).__init__((widgets.Select(choices = all_field_choices()), widgets.Select(choices = [(query_term, query_term_symbols[query_term]) for query_term in query_terms]), widgets.TextInput), attrs)

    def decompress(self, value): 
        if value and isinstance(value, list):
            return value
        elif value and isinstance(value, basestring):
            return value.split(u'|')
        else:
            return [u'']*3

    def format_output(self, rendered_widgets): 
        return u''.join(rendered_widgets) + u"\n<input type='button' value='Delete' onclick='deleteFieldEvent(event);return 0;' />\n"

class SplitHiddenConditionWidget(SplitConditionWidget):
    is_hidden = True

    def __init__(self, attrs=None): 
        super(SplitConditionWidget, self).__init__((widgets.HiddenInput, widgets.HiddenInput, widgets.HiddenInput), attrs)
        for widget in self.widgets:
            widget.input_type = 'hidden'
            widget.is_hidden = True
    
    def format_output(self, rendered_widgets):
        return super(SplitConditionWidget, self).format_output(rendered_widgets)

class FieldValidator(object):
    clean   = lambda self, x: x
    message = _(u'Ensure that you enter a value.')
    code = 'require_value'

    def __call__(self, value):
        cleaned = self.clean(value)
        if cleaned.split(u'|')[0] and not cleaned.split(u'|')[-1]:
            raise ValidationError(
                self.message,
                code=self.code,
                params={},
            )

class SplitConditionField(fields.MultiValueField): 
    widget = SplitConditionWidget
    hidden_widget = SplitHiddenConditionWidget
    default_validators = [FieldValidator()]
    
    def __init__(self, *args, **kwargs): 
        super(SplitConditionField, self).__init__((ChoiceField(choices = all_field_choices()), ChoiceField(choices = [(query_term, query_term_symbols[query_term]) for query_term in query_terms]), CharField()), *args, **kwargs)
    
    def compress(self, data_list): 
        return u'|'.join(data_list)
    
    def validate(self, value): 
        self.run_validators(value)
   
def headingconditionsform_factory(num_conditions = 3): 
    name = "HeadingConditionsForm"
    base = (Form,)
    fields = {'model': ChoiceField(choices=model_choices), 'num_conditions': IntegerField(initial=num_conditions, widget=widgets.HiddenInput)}
    for i in range(num_conditions): 
        fields['condition_'+str(i+1)] = SplitConditionField(initial=[u'', u'exact', u''], required=False, label=u'')
    def as_p(self):
        "Returns this form rendered as HTML <p>s."
        return self._html_output(
            normal_row = u'<p%(html_class_attr)s>%(label)s %(field)s%(help_text)s</p><br /><hr />',
            error_row = u'%s',
            row_ender = '</p><br /><hr />',
            help_text_html = u' <span class="helptext">%s</span>',
            errors_on_separate_row = True)
    fields['as_p'] = as_p
    return type(name, base, fields)

class SplitColumnFieldWidget(widgets.MultiWidget):
    def __init__(self, base_model=None, attrs=None):
        super(SplitColumnFieldWidget, self).__init__((widgets.Select(choices = all_field_choices(base_model=base_model, include_Count=True)), widgets.TextInput), attrs)

    def decompress(self, value): 
        if value and isinstance(value, list):
            return value
        elif value and isinstance(value, basestring):
            return value.split(u'|')
        else:
            return [u'']*2

    def format_output(self, rendered_widgets):
        return u"\n" + u''.join(rendered_widgets) + u"\n<input type='button' value='Delete' onclick='deleteFieldEvent(event);return 0;' />\n"

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
    hidden_widget = SplitHiddenColumnFieldWidget
    default_validators = [FieldValidator()]
    
    def __init__(self, base_model=None, *args, **kwargs): 
        super(SplitColumnFieldField, self).__init__((ChoiceField(choices = all_field_choices(base_model=base_model, include_Count=True)), CharField()), *args, **kwargs)
        self.widget = SplitColumnFieldWidget(base_model=base_model)
    
    def compress(self, data_list): 
        return u'|'.join(data_list)
    
    def validate(self, value): 
        self.run_validators(value)

def displaycolumnsform_factory(base_model=None, num_columns = 3): 
    name = "DisplayColumnsForm"
    base = (Form,)
    fields = {'num_columns': IntegerField(initial=num_columns, widget=widgets.HiddenInput)}
    for i in range(num_columns): 
        fields['column_'+str(i+1)] = SplitColumnFieldField(base_model=base_model, initial=[u'', u''], required=(not i), label=u'')
    def as_p(self):
        "Returns this form rendered as HTML <p>s."
        return self._html_output(
            normal_row = u'<p%(html_class_attr)s>%(label)s %(field)s%(help_text)s</p><br /><hr />',
            error_row = u'%s',
            row_ender = '</p><br /><hr />',
            help_text_html = u' <span class="helptext">%s</span>',
            errors_on_separate_row = True)
    fields['as_p'] = as_p
    return type(name, base, fields)

def pathchoiceform_factory(model, all_paths): 
    name = "PathChoiceForm"
    base = (Form,)
    fields = {}
    for I, target_model, model_paths, field, query_term in all_paths: 
        choices = [[LOOKUP_SEP.join(path+(field,)), label_for_path(model,path,models,many,field=field,links=True)] for (path,models,many) in model_paths]
        field_name = str(I)+'|'+target_model.__name__ + '.' + field
        if not len(choices): 
            pass
        elif len(choices) == 1: 
            fields[field_name] = MultipleChoiceField(choices=choices, widget=widgets.MultipleHiddenInput, initial=[choices[0][0]])
        else: 
            fields[field_name] = MultipleChoiceField(choices=choices, widget=widgets.CheckboxSelectMultiple, label=model.__name__+u'/'+target_model.__name__ + u'.' + field + u'_' + query_term)
    def as_div(self): 
        return self._html_output(
            normal_row = u'<div class="pathgroup" title="&nbsp;"><a class="pathlink" href="" target="_blank">Click here to see a version of this page with links to documenation.</a><br /><br />%(label)s %(field)s%(help_text)s</div>',
            error_row = u'%s',
            row_ender = u'</div>',
            help_text_html = u' <span class="helptext">%s</span>',
            errors_on_separate_row = True)
    fields['as_div'] = as_div
    return type(name, base, fields)

class ModeWizard(DataViewsWizard): 
    
    mode = 1
    first_form = headingconditionsform_factory()
    steps = 4
    
    def title(self, step): 
        if not step: 
            return u'Model and Condition Selection'
        elif step == 1:
            return u'Condition Path Selection'
        elif step == 2: 
            return u'Column Selection'
        elif step == 3: 
            return u'Column Path Selection'
    
    def instructions(self, step): 
        if step in (1,3):
            def format_for_step(s):
                return s % {1: {'field': 'conditions', 'verb': 'conditioned'}, 3: {'field': 'columns', 'verb': 'displayed'}}[step]
            instructions = map(format_for_step, [
u'In the previous step, you selected generic %(field)s, by specifying fields that should be %(verb)s, but not specifying how those fields are related to the base model you selected. Now you must choose the relationships that make the most sense for the output you are trying to generate.', 
# u'In cases where there is only one possible relationship between the base and the selected field, nothing is displayed. Therefore, it is possible for this form to be blank; in this case, just ignore this page and continue.',
])
            if step == 1:
                return instructions + [u'If you selected no conditions, this form will be blank. In this case, just ignore this page and continue.',]
            elif step == 3:
                return instructions + [u'After you complete this page, a spreadsheet of your data will be generated. Depending on the size of your query set, this process may take a while, so please be patient!',]
        elif not step:
            return [
u'Select the conditions of your database query.', 
u'The result of the database query will contain some number of instances of the model you select at the top of this form. In the final output, each row will correspond to exactly one of these instances. For example, if you select ESPUser as the model, each there will be a row of output for every user of the website that matched the query.', 
u'Each subsequent row of this form represents a single condition you may specify. The first drop-down box allows you to select the attribute to condition. The second drop-down box allows you to select the type of condition to apply (the default is equals, but you can apply other relations, as well as text and date searches). The textbox allows you to specify the value to condition on.', 
u'At the end, all conditions are ANDed together (there is currently no support for [(Condition 1) OR (Condition 2)]). Rows can be left blank, and will be ignored. To delete a condition, press \'Delete\', and the row will be cleared of your previous selection. To add more conditions, press \'Add Condition\' at the bottom to add a new row.',
]
        elif step == 2:
            return [
u'Select the columns of your output.', 
u'Each row of this form represents a single column you may specify. The first drop-down box allows you to select the attribute to display. The textbox allows you to specify the text to display in the header of the column.', 
u'All rows except the first (you have to display something!) can be left blank, and will be ignored. To delete a column, press \'Delete\', and the row will be cleared of your previous selection. To add more columns, press \'Add Column\' at the bottom to add a new row.',
]
        
    def done(self, request, form_list):
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
        condition_paths = defaultdict(list)
        headers = []
        for field_name, paths in form_list[1].cleaned_data.iteritems():
            condition_model = globals()[get_mod_func(field_name.partition('|')[2])[0]]
            for path in paths: 
                condition_paths[condition_model].append(path.rpartition(LOOKUP_SEP)[0])
        headers = defaultdict(list)
        view_paths = []
        counts = {}
        for field_name, paths in form_list[3].cleaned_data.iteritems():
            I = int(field_name.partition('|')[0])
            for path in paths:
                if 'Count' in path:
                    path
                    actual_path = path.rpartition(LOOKUP_SEP)[0]
                    path = path.replace(LOOKUP_SEP, u'_')
                    counts[path] = Count(actual_path, distinct=True)
                view_paths.append(path)
                headers[I].append(path)
        if not ('pk' in view_paths or 'id' in view_paths):
            headers[0].append('pk')
        headers = [[path, form_list[2].cleaned_data['column_'+str(I)].split(u'|')[1] if I else self.base_model.__name__ + u' Primary Key ID#'] for I in range(self.num_columns+1) for path in headers[I]]
        queryset = path_v5(self.base_model, condition_paths, *args).annotate(**counts)
        
        fields = [header[0] for header in headers]
        data = {}
        for field in fields:
            data[field] = list(queryset.values_list('pk', field))
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
    
    def process_step(self, form): 
        super(ModeWizard, self).process_step(form)
        self.num_conditions = int(self.request.POST.get('%s-num_conditions' % str(0), 3))
        self.num_columns = int(self.request.POST.get('%s-num_columns' % str(2), 3))
        self.base_model = self.request.POST.get('%s-model' % str(0), None)
        if self.base_model: 
            self.base_model = globals()[self.base_model]
        self.form_list[0] = headingconditionsform_factory(self.num_conditions)
        self.form_list[2] = displaycolumnsform_factory(base_model = self.base_model, num_columns = self.num_columns)
    
        step = int(self.steps.current)
        
        if not form.is_valid():
            return self.render_revalidation_failure(self.request, 0, form)

        if not step: 
            paths = []
            for i in range(self.num_conditions):
                values = form.cleaned_data['condition_'+str(i+1)].split('|')
                if not values[0]: 
                    continue
                condition_model, condition_field = get_mod_func(values[0])
                condition_model = globals()[condition_model]
                paths.append((i+1, condition_model, path_v1(self.base_model, condition_model), condition_field, values[1]))
            self.form_list[step+1] = pathchoiceform_factory(self.base_model, paths)
        elif step == 2:
            paths = []
            for i in range(self.num_columns): 
                values = form.cleaned_data['column_'+str(i+1)].split('|')
                if not values[0]: 
                    continue
                field_model, field_field = get_mod_func(values[0])
                field_model = globals()[field_model]
                paths.append((i+1, field_model, path_v1(self.base_model, field_model), field_field, values[1]))
            self.form_list[step+1] = pathchoiceform_factory(self.base_model, paths)
