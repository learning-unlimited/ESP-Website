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


class ModeForm(forms.Form):
    mode = forms.ChoiceField(choices=[(i, modes[i]) for i in range(len(modes))])
    num_columns = forms.IntegerField(min_value=1)
    num_conditions = forms.IntegerField(min_value=1)

class HeadingConditionsForm(forms.Form):
    model = forms.ChoiceField(choices=model_choices)
    num_conditions = 4
    condition1 = forms.ChoiceField(choices = model_field_choices, required=False)
    query_term1 = forms.ChoiceField(choices = [(query_term, query_term) for query_term in query_terms], initial="exact")
    text1 = forms.CharField(required=False)
    condition2 = forms.ChoiceField(choices = model_field_choices, required=False)
    query_term2 = forms.ChoiceField(choices = [(query_term, query_term) for query_term in query_terms], initial="exact")
    text2 = forms.CharField(required=False)
    condition3 = forms.ChoiceField(choices = model_field_choices, required=False)
    query_term3 = forms.ChoiceField(choices = [(query_term, query_term) for query_term in query_terms], initial="exact")
    text3 = forms.CharField(required=False)
    condition4 = forms.ChoiceField(choices = model_field_choices, required=False)
    query_term4 = forms.ChoiceField(choices = [(query_term, query_term) for query_term in query_terms], initial="exact")
    text4 = forms.CharField(required=False)
    
#    def __init__(self, num_conditions = None, data=None, files=None, auto_id='id_%s', prefix=None,
#                 initial=None, error_class=ErrorList, label_suffix=':',
#                 empty_permitted=False):
#        forms.Form.__init__(self, data, files, auto_id, prefix, initial, error_class, label_suffix, empty_permitted)
#        if num_conditions:
#            self.num_conditions = num_conditions
#        for i in range(self.num_conditions):
#            print i
#            setattr(self, 'condition'+str(i+1), forms.ChoiceField(choices = model_field_choices))

class DisplayColumnForm(forms.Form):
    num_columns = 4
    text1 = forms.CharField(required=False)
    field1 = forms.CharField(required=False)
    text2 = forms.CharField(required=False)
    field2 = forms.CharField(required=False)
    text3 = forms.CharField(required=False)
    field3 = forms.CharField(required=False)
    text4 = forms.CharField(required=False)
    field4 = forms.CharField(required=False)
    


class DataViewsWizard(FormWizard):
    def done(self, request, form_list):
        model = globals()[form_list[1].cleaned_data['model']]
        args = []
        for i in range(form_list[1].num_conditions):
            if not form_list[1].cleaned_data['condition'+str(i+1)]: 
                continue
            condition_model, condition_field = get_mod_func(form_list[1].cleaned_data['condition'+str(i+1)])
            condition_model = globals()[condition_model]
            query_term = form_list[1].cleaned_data['query_term'+str(i+1)]
            text = form_list[1].cleaned_data['text'+str(i+1)]
            val = condition_model._meta.init_name_map()[condition_field][0].to_python(text)
            args.append((condition_model, str(condition_field), str(query_term), val))
        queryset = path_v4(model, *args)
        headers = [ [form_list[2].cleaned_data['field'+str(i+1)], form_list[2].cleaned_data['text'+str(i+1)]] for i in range(form_list[2].num_columns) if form_list[2].cleaned_data['field'+str(i+1)]]
        fields = [header[0] for header in headers]
        data = []
        for item in queryset:
            data.append(dict([ (field , getattr(item, field)) for field in fields]))
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
