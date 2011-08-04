# Create your views here.
from dataviews.forms import ModeForm, DataViewsWizard

def wizard_view(request):
    return DataViewsWizard()(request)

def mode_view(request, mode, **kwargs): 
    form = 'forms_%02d' % int(mode)
    return getattr(__import__('dataviews.forms', globals(), locals(), [form], -1), form).ModeWizard(**kwargs)(request)
