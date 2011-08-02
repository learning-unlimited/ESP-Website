# Create your views here.
from dataviews.forms import ModeForm, DataViewsWizard

def wizard_view(request):
    return DataViewsWizard()(request)

def mode_view(request, mode, **kwargs): 
    form = '%02d_forms' % int(mode)
    return getattr(__import__('dataviews.forms', globals(), locals(), [form], -1), form).ModeWizard(**kwargs)(request)
