from django import forms
from django.shortcuts import render_to_response
from django.contrib.formtools.wizard import FormWizard
from django.template.context import RequestContext
from dataviews import useful_models as all_usefull_models
from dataviews import * 
from django.forms.util import flatatt, ErrorDict, ErrorList
from django.forms.forms import pretty_name
from django.core.urlresolvers import get_callable, get_mod_func
from django.utils.importlib import import_module
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.utils.decorators import method_decorator

useful_models = all_usefull_models[:14]
modes = ["Rows represent instances of a model, columns represent attributes of that model."]
model_choices = [(model.__name__, model.__name__) for model in useful_models]
model_field_choices = [('', "None")]+[(model.__name__,list([(model.__name__+'.'+fieldname, fieldname) for fieldname, field in model._meta.init_name_map().iteritems() if not (isinstance(field[0], RelatedField) or isinstance(field[0], RelatedObject))])) for model in useful_models]
query_term_symbols = {'exact': '[case-sensitive] ==', 'iexact': 'case-insensitive ==', 'contains': 'case-sensitive contains', 'icontains': 'case-insesitive contains', 'gt': '>', 'gte': '>=', 'lt': '<', 'lte': '<=', 'in': 'in',
    'startswith': 'case-sensitive starts with', 'istartswith': 'case-insensitive starts with', 'endswith': 'case-sensitive ends with', 'iendswith': 'case-insensitive ends with', 'range': 'range', 'year': 'year',
    'month': 'month', 'day': 'day', 'week_day': 'week day', 'isnull': 'is null', 'search': 'search', 'regex': 'case-sensitive regex', 'iregex': 'case-insensitive regex'}

class ModeForm(forms.Form):
    mode = forms.ChoiceField(choices=[(i, modes[i]) for i in range(len(modes))])
    num_columns = forms.IntegerField(min_value=1)
    num_conditions = forms.IntegerField(min_value=0)

def headingconditionsform_factory(num_conditions = 1): 
    name = "HeadingConditionsForm"
    base = (forms.Form,)
    fields = {'model': forms.ChoiceField(choices=model_choices)}
    for i in range(num_conditions): 
        fields['condition_'+str(i+1)] = forms.ChoiceField(choices = model_field_choices, required=False)
        fields['query_term_'+str(i+1)] = forms.ChoiceField(choices = [(query_term, query_term_symbol) for query_term, query_term_symbol in query_term_symbols.iteritems()], initial="exact")
        fields['text_'+str(i+1)] = forms.CharField(required=False)
    return type(name, base, fields)

def displaycolumnsform_factory(num_columns = 1): 
    name = "DisplayColumnsForm"
    base = (forms.Form,)
    fields = {}
    for i in range(num_columns): 
        fields['field_'+str(i+1)] = forms.CharField(required=(not i))
        fields['text_'+str(i+1)] = forms.CharField(required=(not i))
    return type(name, base, fields)

def pathchoiceform_factory(model, all_paths): 
    name = "PathChoiceForm"
    base = (forms.Form,)
    fields = {}
    for target_model, model_paths, field in all_paths:
        for (path, models, many) in model_paths: 
            label = unicode(model.__name__)
            if path: 
                for i,n in enumerate(path):
                    label += u' \u2192 ' + pretty_name(n) + u' (' + models[i+1].__name__ + u')'
            label += u' \u2192 ' + pretty_name(unicode(field))
            fields[target_model.__name__ + LOOKUP_SEP + LOOKUP_SEP.join(path)] = forms.BooleanField(required=False, label=label)
    return type(name, base, fields)

class DataViewsWizard(FormWizard):
    
    @method_decorator(admin_required)
    def __call__(self, request, *args, **kwargs):
        return super(DataViewsWizard, self).__call__(request, *args, **kwargs)
    
    def done(self, request, form_list):
        model = globals()[form_list[1].cleaned_data['model']]
        args = []
        for i in range(form_list[0].cleaned_data['num_conditions']):
            if not form_list[1].cleaned_data['condition_'+str(i+1)]: 
                continue
            condition_model, condition_field = get_mod_func(form_list[1].cleaned_data['condition_'+str(i+1)])
            condition_model = globals()[condition_model]
            query_term = form_list[1].cleaned_data['query_term_'+str(i+1)]
            text = form_list[1].cleaned_data['text_'+str(i+1)]
            val = condition_model._meta.init_name_map()[condition_field][0].to_python(text)
            args.append((condition_model, str(condition_field), str(query_term), val))
        paths = defaultdict(list)
        for model_and_path, value in form_list[2].cleaned_data.iteritems():
            if value: 
                condition_model, _, path = model_and_path.partition(LOOKUP_SEP)
                paths[globals()[condition_model]].append(path)
        queryset = path_v5(model, paths, *args)
        headers = [ [form_list[3].cleaned_data['field_'+str(i+1)], form_list[3].cleaned_data['text_'+str(i+1)]] for i in range(form_list[0].cleaned_data['num_columns']) if form_list[3].cleaned_data['field_'+str(i+1)]]
        fields = [header[0] for header in headers]
        data = []
        for item in queryset: 
            item_dict = {}
            for field in fields:
                attributes = field.split('.')
                new_item = [item][:][0]
                for attribute in attributes:
                    new_item = [getattr(new_item, attribute)][:][0]
                item_dict[field] = new_item
            data.append(item_dict)
        from tempfile import TemporaryFile
        from xlwt import Workbook
        book = Workbook()
        sheet1 = book.add_sheet('Sheet 1')
        field_locations = {}
        for j, header in enumerate(headers):
            sheet1.write(0,j,header[1])
            field_locations[header[0]] = j
        for i in range(0, queryset.count()):
            for field in fields:
                sheet1.write(i+1,field_locations[field], data[i][field])
        response = HttpResponse(mimetype="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename=%s' % 'DataViews.xls'
        book.save(response)
        return response

        # return HttpResponseRedirect('/page-to-redirect-to-when-done/')
    
    def get_template(self, step):
        return 'dataviews/forms/wizard.html'
    
    def process_step(self, request, form, step): 
        form0 = self.get_form(0, request.POST)
        if not form0.is_valid():
            return self.render_revalidation_failure(request, 0, form0)
        if not step: 
            self.form_list[1] = headingconditionsform_factory(form0.cleaned_data['num_conditions'])
        if step == 1: 
            model = globals()[form.cleaned_data['model']]
            paths = []
            for i in range(form0.cleaned_data['num_conditions']):
                if not form.cleaned_data['condition_'+str(i+1)]: 
                    continue
                condition_model, condition_field = get_mod_func(form.cleaned_data['condition_'+str(i+1)])
                condition_model = globals()[condition_model]
                paths.append((condition_model, path_v1(model, condition_model), condition_field))
            self.form_list[2] = pathchoiceform_factory(model, paths)
        if step == 2:
            self.form_list[3] = displaycolumnsform_factory(form0.cleaned_data['num_columns'])
