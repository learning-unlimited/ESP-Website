from django.forms import *
from dataviews import * 
from django.forms.forms import pretty_name
from django.core.urlresolvers import get_mod_func
from django.http import Http404, HttpResponseRedirect, HttpResponse
from esp.dataviews.forms import *

def headingconditionsform_factory(num_conditions = 3): 
    name = "HeadingConditionsForm"
    base = (Form,)
    fields = {'model': ChoiceField(choices=model_choices), 'num_conditions': IntegerField(initial=num_conditions, widget=widgets.HiddenInput)}
    for i in range(num_conditions): 
        fields['condition_'+str(i+1)] = ChoiceField(choices = model_field_choices, required=False)
        fields['query_term_'+str(i+1)] = ChoiceField(choices = [(query_term, query_term_symbols[query_term]) for query_term in query_terms], initial="exact")
        fields['text_'+str(i+1)] = CharField(required=False)
    return type(name, base, fields)

def displaycolumnsform_factory(num_columns = 3): 
    name = "DisplayColumnsForm"
    base = (Form,)
    fields = {'num_columns': IntegerField(initial=num_columns, widget=widgets.HiddenInput)}
    for i in range(num_columns): 
        fields['field_'+str(i+1)] = ChoiceField(choices = model_field_choices, required=(not i))
        fields['text_'+str(i+1)] = CharField(required=(not i))
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

    def __init__(self, initial=None): 
        super(ModeWizard, self).__init__(form_list=[headingconditionsform_factory()]*4, initial=initial)
    
    def done(self, request, form_list):
        model = globals()[form_list[1].cleaned_data['model']]
        args = []
        for i in range(form_list[1].cleaned_data['num_conditions']):
            if not form_list[1].cleaned_data['condition_'+str(i+1)]: 
                continue
            condition_model, condition_field = get_mod_func(form_list[1].cleaned_data['condition_'+str(i+1)])
            condition_model = globals()[condition_model]
            query_term = form_list[1].cleaned_data['query_term_'+str(i+1)]
            text = form_list[1].cleaned_data['text_'+str(i+1)]
            val = condition_model._meta.init_name_map()[condition_field][0].to_python(text)
            args.append((condition_model, str(condition_field), str(query_term), val))
        paths = defaultdict(list)
        view_paths = []
        headers = []
        for model_and_path, value in form_list[2].cleaned_data.iteritems():
            if value: 
                _, _, model_and_path = model_and_path.partition('|')
                condition_model, _, path = model_and_path.partition(LOOKUP_SEP)
                path, _, _ = path.rpartition(LOOKUP_SEP)
                paths[globals()[condition_model]].append(path)
        for model_and_path, value in form_list[4].cleaned_data.iteritems():
            if value: 
                I, _, model_and_path = model_and_path.partition('|')
                _, _, path = model_and_path.partition(LOOKUP_SEP)
                view_paths.append(path)
                headers.append([path, form_list[3].cleaned_data['text_'+I]])
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
    
    def process_step(self, request, form, step): 
        form1 = None
        model = None
        num_conditions = int(request.POST.get('%s-num_conditions' % self.prefix_for_step(1), 3))
        num_columns = int(request.POST.get('%s-num_columns' % self.prefix_for_step(3), 3))
        if not step: 
            self.form_list[1] = headingconditionsform_factory(num_conditions)
        else:
            form1 = self.get_form(1, request.POST)
            if not form1.is_valid():
                return self.render_revalidation_failure(request, 1, form1)
            model = globals()[form1.cleaned_data['model']]
        if step == 1: 
            paths = []
            for i in range(num_conditions):
                if not form.cleaned_data['condition_'+str(i+1)]: 
                    continue
                condition_model, condition_field = get_mod_func(form.cleaned_data['condition_'+str(i+1)])
                condition_model = globals()[condition_model]
                paths.append((i+1, condition_model, path_v1(model, condition_model), condition_field))
            self.form_list[2] = pathchoiceform_factory(model, paths)
        if step == 2:
            self.form_list[3] = displaycolumnsform_factory(num_conditions)
        if step == 3: 
            paths = []
            for i in range(num_columns):
                if not form.cleaned_data['field_'+str(i+1)]: 
                    continue
                field_model, field_field = get_mod_func(form.cleaned_data['field_'+str(i+1)])
                field_model = globals()[field_model]
                paths.append((i+1, field_model, path_v1(model, field_model), field_field))
            self.form_list[4] = pathchoiceform_factory(model, paths)
