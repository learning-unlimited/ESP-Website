from django import forms

class RemoteTeacherProfileForm(forms.ModelForm):
    volunteer = forms.BooleanField(required = False)
    need_bus = forms.BooleanField(required = False)

    def __init__(self, module=None, *args, **kwargs):
	self.base_fields['volunteer_times'] = forms.MultipleChoiceField(required = False, choices = module.getTimes())
	forms.ModelForm.__init__(self, *args, **kwargs)
    
    class Meta:
	from esp.program.modules.module_ext import RemoteProfile
	model = RemoteProfile
	fields = ('volunteer', 'need_bus', 'volunteer_times')
