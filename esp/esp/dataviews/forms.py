from django import forms
from django.shortcuts import render_to_response
from django.contrib.formtools.wizard import FormWizard
from django.template.context import RequestContext
from dataviews import useful_models as all_usefull_models
from dataviews import * 
from django.forms.util import flatatt, ErrorDict, ErrorList
from django.core.urlresolvers import get_callable, get_mod_func
from django.utils.importlib import import_module
from django.http import Http404, HttpResponseRedirect, HttpResponse

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
        queryset = path_v4(model, *args)
        headers = [ [form_list[2].cleaned_data['field_'+str(i+1)], form_list[2].cleaned_data['text_'+str(i+1)]] for i in range(form_list[0].cleaned_data['num_columns']) if form_list[2].cleaned_data['field_'+str(i+1)]]
        fields = [header[0] for header in headers]
        data = []
        for item in queryset: 
            item_dict = {}
            for field in fields:
                attributes = field.split('.')
                print attributes
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
        if self.num_steps() == 1 and not step: 
            self.form_list.append(headingconditionsform_factory(form.cleaned_data['num_conditions']))
            self.form_list.append(displaycolumnsform_factory(form.cleaned_data['num_columns']))
