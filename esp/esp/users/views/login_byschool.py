from django import forms
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import REDIRECT_FIELD_NAME
from esp.forms import SizedCharField, BlankSelectWidget, FormWithRequiredCss
from esp.web.util.main import render_to_response
from esp.users.models import ESPUser, K12School

class SchoolSelectForm(FormWithRequiredCss):
    """ Form that lets a student pick their school. """
    school = forms.ChoiceField(label='School', choices=[], widget=BlankSelectWidget(blank_choice=('','Pick your school from this list...')))
    def __init__(self, *args, **kwargs):
        super(SchoolSelectForm, self).__init__(*args, **kwargs)
        self.fields['school'].choices = [(x.id, x.name) for x in K12School.objects.order_by('name')] + [('0', 'Other')]

class StudentSelectForm(FormWithRequiredCss):
    """ Form that lets a student pick themselves from a list. """    
    username = forms.ChoiceField(label='Your name', choices=[], widget=BlankSelectWidget(blank_choice=('','Pick your name from this list...')))
    def __init__(self, students=[], *args, **kwargs):
        super(StudentSelectForm, self).__init__(*args, **kwargs)
        self.fields['username'].choices=students

class BarePasswordForm(FormWithRequiredCss):
    """ Just a password. """
    password = forms.CharField(label='Password', widget=forms.PasswordInput())

def login_byschool(request, *args, **kwargs):
    """ Let a student pick their school. """
    
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')
    redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME, '')
    redirect_str = u''
    if redirect_to:
        redirect_str = u'?%s=%s' % (REDIRECT_FIELD_NAME, redirect_to)
    
    if request.method == 'POST':
        form = SchoolSelectForm(request.POST)
        if form.is_valid():
            sid = form.cleaned_data['school']
            if sid == '0': # Picked other
                return HttpResponseRedirect( '/myesp/register/' )
            return HttpResponseRedirect(u'/myesp/login/byschool/%s/%s' % (sid, redirect_str))
    else:
        form = SchoolSelectForm()
    
    return render_to_response('registration/login_byschool.html', request, request.get_node('Q/Web/myesp'),
        { 'form': form, 'action': request.get_full_path(), 'redirect_field_name': REDIRECT_FIELD_NAME, 'next': redirect_to, 'pwform': BarePasswordForm().as_table() })

def login_byschool_pickname(request, school_id, *args, **kwargs):
    """ Let a student pick their name. """
    
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')
    redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME, '')
    redirect_str = u''
    if redirect_to:
        redirect_str = u'?%s=%s' % (REDIRECT_FIELD_NAME, redirect_to)
    
    # Get the school
    school_set = K12School.objects.filter(id=school_id)
    if school_set.count() < 1:
        return HttpResponseRedirect( '/myesp/login/byschool/%s' % redirect_str )
    school = school_set[0]
    
    if request.method == 'POST' and request.POST.has_key('username'):
        preset_username = request.POST['username']
        if preset_username == '-1':
            return HttpResponseRedirect( '/myesp/register/' )
        form = BarePasswordForm()
        action = '/myesp/login/'
    else:
        # Prepare a new student-select box
        candidate_users = ESPUser.objects.filter( registrationprofile__student_info__k12school=school.id ).distinct().order_by('first_name', 'id')
        form = StudentSelectForm( students=[ (s.username, '%s (%s)' % (s.name(), s.username)) for s in candidate_users ] + [('-1', 'I don\'t see my name in this list...')] )
        preset_username = ''
        action = request.get_full_path()
        if request.REQUEST.has_key('dynamic'):
            return HttpResponse( form.as_table() )
    
    return render_to_response('registration/login_byschool_pickname.html', request, request.get_node('Q/Web/myesp'),
        { 'form': form, 'action': action, 'redirect_field_name': REDIRECT_FIELD_NAME, 'next': redirect_to, 'preset_username': preset_username })
