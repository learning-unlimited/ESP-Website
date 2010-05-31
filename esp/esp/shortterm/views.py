# Create your views here.

from django import forms
from esp.shortterm.models import ResponseForm, VolunteerRegistration
from django.http import HttpResponseRedirect, HttpResponse
from esp.web.util.main import render_to_response
from esp.utils.forms import EmailModelForm
from esp.datatree.models import *
from esp.users.models import admin_required
from esp.shortterm.models import ResponseForm
from esp.shortterm.crazy_excel_thing import build_workbook

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

@admin_required
def excel_survey_responses(request):
    response = HttpResponse(build_workbook().getvalue(), mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=esp-survey-results-all.xls'
    return response
class VolunteerRegistrationForm(EmailModelForm):
    class Meta:
        model = VolunteerRegistration

def volunteer_signup(request):
    volunteer_anchor = GetNode('Q/Web/getinvolved')
    if request.POST:
        response = VolunteerRegistrationForm(request.POST)
        if response.is_valid():
            data = response.save(from_addr='Splash! Chicago <server@uchicago-splash.mit.edu>', destination_addrs=['Race Wright <rwright@uchicago.edu>'])
            return render_to_response("shortterm/volunteer_signup/complete.html", request, context={'anchor': volunteer_anchor})
    else:
        response = VolunteerRegistrationForm()

    return render_to_response("shortterm/volunteer_signup/form.html", request, context={'form': response, 'anchor': volunteer_anchor})


def advertisement_redirect(request):

    ipaddr = ''
    if 'HTTP_X_FORWARDED_FOR' in request.META:
      ipaddr = request.META['HTTP_X_FORWARDED_FOR']
    elif 'REMOTE_ADDR' in request.META:
      ipaddr = request.META['REMOTE_ADDR']

    agent = ''
    if 'HTTP_USER_AGENT' in request.META:
      agent = request.META['HTTP_USER_AGENT']

    entry = AdLogEntry()
    entry.ts = datetime.datetime.today()
    entry.ipaddr = ipaddr[0:31]
    entry.agent = agent[0:255]
    entry.save()
    return HttpResponseRedirect("/learn/index.html")
