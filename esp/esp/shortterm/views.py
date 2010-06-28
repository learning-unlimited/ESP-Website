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

@admin_required
def excel_survey_responses(request):
    response = HttpResponse(build_workbook().getvalue(), mimetype='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=esp-survey-results-all.xls'
    return response

@login_required
def logistics_quiz_start(request):
    def _continue():
        return HttpResponseRedirect("/teach/Spark/quiz.html")
    def _stop():
        return HttpResponseRedirect("/teach/Spark/quiz_stop.html")
    if request.user.isTeacher():
        if request.user.getTaughtClasses().filter(status=10, parent_program__anchor__parent__name__in=['Splash','Spark','SplashOnWheels','Junction','HSSP']):
            return _continue()
    return _stop()

@login_required
def logistics_quiz_check(request):
    from esp.middleware import ESPError
    from esp.users.models import UserBit
    from esp.datatree.models import GetNode

    def _back():
        return HttpResponseRedirect("/teach/Spark/quiz.html")
    def _fail(key=None):
        numbers = {
            'prog_month': 1,
            'prog_day': 1,
            'photo_exists': 7,
            'call_911': 8,
            'teacher_lunch': 9,
            'check_in': 10,
            'sec1': 5,
            'sec2': 5,
            'sec3': 5,
            'sec4': 5,
            'sec5': 5,
            'sec6': 5,
            
            'reimburse1': 6,
            'reimburse2': 6,
            'reimburse3': 6,
            'reimburse4': 6,

            'security_number': 4,
            'room_number': 2,
            'first_class': 3,
        }
        if key is not None:
            raise ESPError(False), "We're sorry; you gave an incorrect answer to question %d. Please use your browser's back button to return to the quiz and check your answers." % numbers[key]
        return HttpResponseRedirect("/teach/Spark/quiz_tryagain.html")
    correct_answers = {
        'prog_month': '3',
        'prog_day': '13',
        'photo_exists': 'False',
        'call_911': 'False',
        'teacher_lunch': 'True',
        'check_in': 'True',
    }
    checkboxes = {
        'sec1': True,
        'sec2': False,
        'sec3': True,
        'sec4': False,
        'sec5': True,
        'sec6': True,
        
        'reimburse1': True,
        'reimburse2': False,
        'reimburse3': False,
        'reimburse4': True,
    }
    
    if not request.POST or not request.user.isTeacher():
        return _back()
    if not request.user.getTaughtClasses().filter(status=10, parent_program__anchor__parent__name__in=['Splash','Spark','SplashOnWheels','Junction','HSSP']):
        return HttpResponseRedirect("/teach/Spark/quiz_stop.html")

    for key in correct_answers:
        if request.POST.get(key, '') != correct_answers[key]:
            return _fail(key)
    for key in checkboxes:
        if bool(request.POST.get(key, False)) != checkboxes[key]:
            return _fail(key)
    ans = request.POST.get('security_number', '')
    if ''.join([x for x in ans if x.isdigit()]) != '6172534941':
        return _fail('security_number')
    
    first_class = request.user.getTaughtSections().filter(parent_class__parent_program=47, status=10).order_by('meeting_times') or [None]
    first_class = first_class[0]
    if first_class is None:
        raise ESPError(False), "You don't have any classes scheduled! Please talk to the directors."
    else:
        ans = request.POST.get('room_number', '')
        if ans.strip() not in first_class.prettyrooms():
            return _fail('room_number')
        ans = request.POST.get('first_class')
        if ans == first_class.meeting_times.order_by('start')[0].start.hour:
            return _fail('first_class')
    
    ub, created = UserBit.objects.get_or_create(user=request.user, qsc=GetNode('Q/Programs/Spark/2010'), verb=GetNode('V/Flags/Registration/Teacher/QuizDone'))
    if not created:
        ub.renew()
    return HttpResponseRedirect("/teach/Spark/quiz_success.html")

