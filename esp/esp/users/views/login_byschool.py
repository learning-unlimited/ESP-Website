from django import forms
from django.http import HttpResponseRedirect
from django.contrib.auth import REDIRECT_FIELD_NAME
from esp.forms import SizedCharField, BlankSelectWidget, FormWithRequiredCss
from esp.web.util.main import render_to_response
from esp.users.models import ESPUser, K12School

class SchoolSelectForm(FormWithRequiredCss):
    """ Form that lets a student pick their school and search for themselves. """
    
    school = forms.ModelChoiceField(label='School', queryset=K12School.objects.order_by('name'),
                                    help_text='If your school does not appear in the list, you may <a href="/myesp/register">create a new account</a>.')
    last_name_start = forms.CharField(label='Last name', help_text='Enter at least the first few (2-5) letters of your last name.', max_length=30)


class StudentSelectLoginForm(FormWithRequiredCss):
    """
    Like the usual login form, except the username is picked from a list.
    Not used to validate input; stuff entered in this form is sent through the usual login pipeline.
    """
    
    username = forms.ChoiceField(label='Your name', choices=[], widget=BlankSelectWidget(),
                                help_text='If your name does not appear in the list, you may <a href="" onclick="history.go(-1); return false;">go back and try again</a> or <a href="/myesp/register">create a new account</a>.')
    password = forms.CharField(label='Password', widget=forms.PasswordInput())
    
    def __init__(self, students=[], *args, **kwargs):
        super(StudentSelectLoginForm, self).__init__(*args, **kwargs)
        self.fields['username'].choices=students


def login_byschool(request, *args, **kwargs):
    """ Let a student pick their school and search for themselves. """
    
    if request.user.is_authenticated():
        return HttpResponseRedirect('/')
    
    redirect_to = request.REQUEST.get(REDIRECT_FIELD_NAME, '')
    
    if request.method == 'POST':
        form = SchoolSelectForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            candidate_users = ESPUser.objects.filter( last_name__istartswith=cleaned_data['last_name_start'],
                                  registrationprofile__student_info__k12school=cleaned_data['school'] ).distinct().order_by('first_name', 'id')
            nextform = StudentSelectLoginForm( students=[ (s.username, '%s (%s)' % (s.name(), s.username)) for s in candidate_users ] )
            return render_to_response('registration/login_byschool_pickname.html', request,
                                      request.get_node('Q/Web/myesp'), { 'form': nextform, 'next': redirect_to })
    else:
        
        form = SchoolSelectForm()
    
    return render_to_response('registration/login_byschool.html', request,
                              request.get_node('Q/Web/myesp'), { 'form': form, 'next': redirect_to })
