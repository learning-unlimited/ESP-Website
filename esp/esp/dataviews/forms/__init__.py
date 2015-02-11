from django.forms import *
from django.contrib.formtools.wizard.views import SessionWizardView
from dataviews import useful_models as all_usefull_models
from dataviews import *
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator

useful_models = all_usefull_models
modes = ["""Rows represent instances of a model,
            columns represent attributes of that model."""]
model_choices = [('', 'Select a base model.')] + \
                [(model.__name__, model.__name__) for model in useful_models]

query_term_symbols = {
    'exact': '[case-sensitive] ==',
    'iexact': 'case-insensitive ==',
    'contains': 'case-sensitive contains',
    'icontains': 'case-insesitive contains',
    'gt': '>',
    'gte': '>=',
    'lt': '<',
    'lte': '<=',
    'in': 'in',
    'startswith': 'case-sensitive starts with',
    'istartswith': 'case-insensitive starts with',
    'endswith': 'case-sensitive ends with',
    'iendswith': 'case-insensitive ends with',
    'range': 'range',
    'year': 'year',
    'month': 'month',
    'day': 'day',
    'week_day': 'week day',
    'isnull': 'is null',
    'search': 'search',
    'regex': 'case-sensitive regex',
    'iregex': 'case-insensitive regex'
}


class ModeForm(Form):
    mode = ChoiceField(choices=([('', 'Choose a mode. Note: there is currently only one mode.')] +
                                [(i + 1, modes[i]) for i in range(len(modes))]), required=True)


class DataViewsWizard(SessionWizardView):

    mode = 0
    first_form = ModeForm
    steps = 1

    def title(self, step=0):
        if not step:
            return u'Mode Selection'

    def instructions(self, step=0):
        if not step:
            return [u'Select the type of output you would like to generate.']

    def get_context_data(self, form, **kwargs):
        # get context data to be passed to the respective templates
        context = super(DataViewsWizard, self).get_context_data(form=form, **kwargs)
        context['title'] = u'%s - DataViews Mode %02d' % (self.title(step), self.mode)
        context['instructions'] = self.instructions(step)
        return context

    def get_template_names(self):
        step = int(self.steps.current)

        def format_for_mode(s):
            return s % {'mode': self.mode, 'step': step + 1}

        return map(format_for_mode, ('dataviews/forms_%(mode)02d/%(step)02d_wizard.html',
                                     'dataviews/forms_%(mode)02d/wizard.html',
                                     'dataviews/forms/%(step)02d_wizard.html',
                                     'dataviews/forms/wizard.html'))

    def done(self, request, form_list):
        return HttpResponseRedirect('/dataviews/mode%02d/'% int(form_list[0].cleaned_data['mode']))

    @method_decorator(admin_required)
    def dispatch(self, *args, **kwargs):
        return super(DataViewsWizard, self).dispatch(*args, **kwargs)

    