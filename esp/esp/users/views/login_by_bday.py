from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import REDIRECT_FIELD_NAME
from esp.middleware import ESPError
from esp.utils.forms import FormWithRequiredCss
from esp.utils.web import render_to_response
from esp.web.views.main import registration_redirect
from esp.users.models import ESPUser
from esp.users.views.login_byschool import StudentSelectForm, BarePasswordForm
from django.conf import settings
from django.db.models.query import Q

month_choices = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
month_choices = [('', '')] + [(i + 1, month_choices[i]) for i in range(len(month_choices))]
day_choices = range(1, 32)
day_choices = [(d, d) for d in day_choices]
class BirthdaySelectForm(FormWithRequiredCss):
    """ Form that lets a student pick their school. """
    month = forms.ChoiceField(label='Month', choices=month_choices)
    day = forms.ChoiceField(label='Day', choices=day_choices)

def login_by_bday(request, *args, **kwargs):
    """ Let a student pick their school. """

    if request.user.is_authenticated():
        return registration_redirect(request)

    redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME, settings.DEFAULT_REDIRECT)
    redirect_str = u''
    if redirect_to:
        redirect_str = u'?%s=%s' % (REDIRECT_FIELD_NAME, redirect_to)

    if request.method == 'POST':
        form = BirthdaySelectForm(request.POST)
        if form.is_valid():
            month = form.cleaned_data['month']
            day = form.cleaned_data['day']
            return HttpResponseRedirect(u'/myesp/login/bybday/%s/%s/%s' % (month, day, redirect_str))
    else:
        form = BirthdaySelectForm()

    return render_to_response('registration/login_by_bday.html', request,
        { 'form': form, 'action': request.get_full_path(), 'redirect_field_name': REDIRECT_FIELD_NAME, 'next': redirect_to, 'pwform': BarePasswordForm().as_table() })

def login_by_bday_pickname(request, month, day, *args, **kwargs):
    """ Let a student pick their name. """

    if request.user.is_authenticated():
        return registration_redirect(request)

    redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME, settings.DEFAULT_REDIRECT)
    redirect_str = u''
    if redirect_to:
        redirect_str = u'?%s=%s' % (REDIRECT_FIELD_NAME, redirect_to)

    if request.method == 'POST' and 'username' in request.POST:
        preset_username = request.POST['username']
        if preset_username == '-1':
            return HttpResponseRedirect( '/myesp/register/' )
        form = BarePasswordForm()
        action = '/myesp/login/'
    else:
        #   Add the birthday information to the user's session
        request.session['birth_month'] = month
        request.session['birth_day'] = day

        # Prepare a new student-select box
        user_filter = Q(registrationprofile__student_info__dob__month=month, registrationprofile__student_info__dob__day=day)
        candidate_users = ESPUser.objects.filter(is_active=True).filter(user_filter).distinct().order_by('first_name', 'id')
        form = StudentSelectForm( students=[ (s.username, '%s (%s)' % (s.first_name, s.username)) for s in candidate_users ] + [('-1', 'I don\'t see my name in this list...')] )
        preset_username = ''
        action = request.get_full_path()
        if 'dynamic' in request.REQUEST:
            return HttpResponse( form.as_table() )

    return render_to_response('registration/login_by_bday_pickname.html', request,
        { 'form': form, 'action': action, 'redirect_field_name': REDIRECT_FIELD_NAME, 'next': redirect_to, 'preset_username': preset_username })

def login_by_bday_new(request):
    """ Save the user's birthday in the session variable and redirect to account creation. """
    if request.method == 'POST':
        form = BirthdaySelectForm(request.POST)
        if form.is_valid():
            month = form.cleaned_data['month']
            day = form.cleaned_data['day']
            request.session['birth_month'] = month
            request.session['birth_day'] = day
        else:
            raise ESPError(str(form.errors), log=False)
    return HttpResponseRedirect( '/myesp/register/' )
