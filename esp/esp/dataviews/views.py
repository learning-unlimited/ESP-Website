# Create your views here.
from esp.web.util.main import render_to_response
from esp.dataviews import *
from esp.dataviews.forms import ModeForm, DataViewsWizard
from django.db.models.related import RelatedObject
from django.db.models.fields.related import RelatedField, ForeignKey, ManyToManyField

def wizard_view(request):
    return DataViewsWizard()(request)

def mode_view(request, mode, **kwargs): 
    form = 'forms_%02d' % int(mode)
    return getattr(__import__('dataviews.forms', globals(), locals(), [form], -1), form).ModeWizard(**kwargs)(request)

def doc_view(request, model_name): 
    context = defaultdict(list)
    context['useful_models'] = [model.__name__ for model in useful_models]
    context['model_name'] = model_name
    context['model'] = globals()[model_name]
    context['module'] = context['model']._meta.app_label + '.' + context['model'].__name__.lower()
    for name, field in context['model']._meta.init_name_map().iteritems(): 
        field = field[0]
        if isinstance(field, ManyToManyField):
            context['many'].append((name, field.rel.to.__name__))
        elif isinstance(field, RelatedField): 
            context['forward'].append((name, field.rel.to.__name__))
        elif isinstance(field, RelatedObject):
            context['reverse'].append((name, field.field.model.__name__))
        else:
            context['fields'].append((name, field.__class__.__name__))
    return render_to_response('dataviews/doc.html', request, context)

def path_view(request, model1_name, model2_name): 
    context = defaultdict(list)
    context['base_model_name'] = model1_name
    context['model_name'] = model2_name
    context['base_model'] = globals()[model1_name]
    context['model'] = globals()[model2_name]
    context['labels'] = [label_for_path(context['base_model'], path, models, many, links=True) for (path,models,many) in path_v1(context['base_model'], context['model'])]
    return render_to_response('dataviews/paths.html', request, context)
    
    
