from django.forms import *
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

useful_models = all_usefull_models
modes = ["Rows represent instances of a model, columns represent attributes of that model."]
model_choices = [(model.__name__, model.__name__) for model in useful_models]
model_field_choices = [('', "None")]+[(model.__name__,list([(model.__name__+'.'+fieldname, fieldname) for fieldname, field in model._meta.init_name_map().iteritems() if not (isinstance(field[0], RelatedField) or isinstance(field[0], RelatedObject))])) for model in useful_models]
query_term_symbols = {'exact': '[case-sensitive] ==', 'iexact': 'case-insensitive ==', 'contains': 'case-sensitive contains', 'icontains': 'case-insesitive contains', 'gt': '>', 'gte': '>=', 'lt': '<', 'lte': '<=', 'in': 'in',
    'startswith': 'case-sensitive starts with', 'istartswith': 'case-insensitive starts with', 'endswith': 'case-sensitive ends with', 'iendswith': 'case-insensitive ends with', 'range': 'range', 'year': 'year',
    'month': 'month', 'day': 'day', 'week_day': 'week day', 'isnull': 'is null', 'search': 'search', 'regex': 'case-sensitive regex', 'iregex': 'case-insensitive regex'}

class ModeForm(Form):
    mode = ChoiceField(choices=[(i+1, modes[i]) for i in range(len(modes))])

class DataViewsWizard(FormWizard):
    
    mode = 0
    first_form = ModeForm
    steps = 1
    
    def __init__(self, initial=None):
        super(DataViewsWizard, self).__init__(form_list=[self.first_form]*self.steps, initial=initial)
    
    @method_decorator(admin_required)
    def __call__(self, request, *args, **kwargs):
        return super(DataViewsWizard, self).__call__(request, *args, **kwargs)
    
    def get_template(self, step): 
        def format_for_mode(s): 
            return s % {'mode': self.mode, 'step': step}
        return map(format_for_mode, ('dataviews/%(mode)02d_forms/%(step)02d_wizard.html', 'dataviews/%(mode)02d_forms/wizard.html', 'dataviews/forms/%(step)02d_wizard.html', 'dataviews/forms/wizard.html'))
    
    def done(self, request, form_list): 
        return HttpResponseRedirect('/dataviews/mode%02d/' % int(form_list[0].cleaned_data['mode']))
