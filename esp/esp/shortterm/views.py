# Create your views here.

from django import forms
from esp.shortterm.models import ResponseForm, VolunteerRegistration
from django.http import HttpResponseRedirect
from esp.web.util.main import render_to_response
from esp.utils.forms import EmailModelForm
from esp.datatree.models import *

class SchoolResponseForm(forms.ModelForm):
    class Meta:
        model = ResponseForm

def school_response_form(request):
    if request.POST:
        response = SchoolResponseForm(request.POST)
        if response.is_valid():
            data = response.save()
            data.send_mail()
            return HttpResponseRedirect("/school_response/thanks.html")

    else:
        response = SchoolResponseForm()

    return render_to_response("shortterm/school_response/form.html", request, context={ 'form': response })

class VolunteerRegistrationForm(EmailModelForm):
    class Meta:
        model = VolunteerRegistration

def volunteer_signup(request):
    volunteer_anchor = GetNode('Q/Web/getinvolved')
    if request.POST:
        response = VolunteerRegistrationForm(request.POST)
        if response.is_valid():
            data = response.save(from_addr='Stanford ESP <server@stanfordesp.org>', destination_addrs=['Stanford ESP <stanfordesp@gmail.com>'])
            return render_to_response("shortterm/volunteer_signup/complete.html", request, context={'anchor': volunteer_anchor})
    else:
        response = VolunteerRegistrationForm()

    return render_to_response("shortterm/volunteer_signup/form.html", request, context={'form': response, 'anchor': volunteer_anchor})
