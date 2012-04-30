from esp.users.models import User, UserBit, ESPUser_Profile, ESPUser
from esp.users.forms.user_reg import UserRegForm, EmailUserForm, EmailUserRegForm
from esp.web.util.main import render_to_response
from esp.datatree.models import GetNode
from esp.mailman import add_list_member
from esp.middleware.esperrormiddleware import ESPError
from esp.tagdict.models import Tag
from django.contrib.auth import login, authenticate
from django.http import HttpResponseRedirect
from django.template import loader
from esp.middleware.threadlocalrequest import AutoRequestContext as Context
from esp.dbmail.models import send_mail
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
import hashlib
import random
from esp import settings
from django.utils.datastructures import MultiValueDictKeyError

__all__ = ['join_emaillist','user_registration_phase1', 'user_registration_phase2']

def join_emaillist(request):
    """
    View to join our email list.
    """

    if request.user.is_authenticated():
        return render_to_response('registration/already_logged_in.html',
                                  request, request.get_node('Q/Web/myesp'), {})


    if request.method == 'POST':
        form = EmailUserForm(request.POST, request=request)


        if form.is_valid():
            # create the user
            User.objects.get_or_create(email    = form.cleaned_data['email'],
                                       username = form.cleaned_data['email'],
                                       password = 'emailuser')

            add_list_member('announcements', form.cleaned_data['email'])

            return HttpResponseRedirect('/')
    else:
        form = EmailUserRegForm(request=request)    

    return render_to_response('registration/emailuser.html',
                              request, request.get_node('Q/Web/myesp'), {'form':form})


def user_registration_validate(request):    
    form = UserRegForm(request.POST)

    if form.is_valid():         
        print "form valid"
        #I'm not sure what all the try/catch is here, but it possibly has to do with dummy volunteer accounts
        try:
            user = ESPUser.objects.get(email=form.cleaned_data['email'],
                                       password = 'emailuser')
        except User.DoesNotExist:
            try:
                user = ESPUser.objects.filter(username = form.cleaned_data['username'],
                                              is_active = False).latest('date_joined')
            except User.DoesNotExist:
                user = ESPUser(email = form.cleaned_data['email'])

            user.username   = form.cleaned_data['username']
            user.last_name  = form.cleaned_data['last_name']
            user.first_name = form.cleaned_data['first_name']
            user.set_password(form.cleaned_data['password'])
            
            #   Append key to password and disable until activation if desired
            if Tag.getTag('require_email_validation', default='False') == 'True':
                userkey = random.randint(0,2**31 - 1)
                user.password += "_%d" % userkey
                user.is_active = False

            user.save()
            ESPUser_Profile.objects.get_or_create(user = user)

            role_verb = GetNode('V/Flags/UserRole/%s' % form.cleaned_data['initial_role'])

            role_bit  = UserBit.objects.create(user = user,
                                               verb = role_verb,
                                               qsc  = request.get_node('Q'),
                                               recursive = False)

            if Tag.getTag('require_email_validation', default='False') == 'False':
                user = authenticate(username=form.cleaned_data['username'],
                                    password=form.cleaned_data['password'])
                
                login(request, user)
                return HttpResponseRedirect('/myesp/profile/')
            else:
                from django.template import Context as RawContext
                t = loader.get_template('registration/activation_email.txt')
                c = RawContext({'user': user, 'activation_key': userkey, 'site': Site.objects.get_current()})

                send_mail("Account Activation", t.render(c), settings.SERVER_EMAIL, [user.email], fail_silently = False)

                return render_to_response('registration/account_created_activation_required.html',
                                          request, request.get_node('Q/Web/myesp'),
                                          {'user': user, 'site': Site.objects.get_current()})
        else:
            print "form not valid"
            return render_to_response('registration/newuser.html',
                                      request, request.get_node('Q/Web/myesp'),{'form':form})

def user_registration_checkemail(request):
    """Method to handle the first phase of registration when submitted as a form.

The method user_registration_phase1 calls this function when it's given a POST request.
When the form isn't valid, re-render the same template but with the form errors.
When there are already accounts with this email address (depending on some tags), give the user information about them before proceeding.
"""
    form = EmailUserRegForm(request.POST)

    if form.is_valid():         
            ## First, check to see if we have any users with the same e-mail
        if not 'do_reg_no_really' in request.POST and  Tag.getTag('ask_about_duplicate_accounts', default='False') == 'True':
            existing_accounts = ESPUser.objects.filter(email=form.cleaned_data['email'], is_active=True).exclude(password='emailuser')
            if len(existing_accounts) != 0:
                    #they have accounts. go back to the same page, but ask them
                    #if they want to try to log in
                return render_to_response('registration/newuser_phase1.html',
                                          request, request.get_node('Q/Web/myesp'),
                                          { 'accounts': existing_accounts, 'email':form.cleaned_data['email'], 'site': Site.objects.get_current(), 'form': form })    
            #form is valid, and not multiple accounts 
            return HttpResponseRedirect(reverse('users.views.user_registration_phase2')+'?email='+form.cleaned_data['email'])#some nonclean for urls issue to be fixed later
        else: #form is not valid
            return render_to_response('registration/newuser_phase1.html',
                                      request, request.get_node('Q/Web/myesp'),
                                      {'form':form, 'site': Site.objects.get_current()})
    

def user_registration_phase1(request):
    """Displays phase 1, and recieves and passes off phase 1 submissions."""
    if request.user.is_authenticated():
        return render_to_response('registration/already_logged_in.html',
                                  request, request.get_node('Q/Web/myesp'), {})

    if request.method == 'POST':
        return user_registration_checkemail(request)
    else: 
        form=EmailUserRegForm()
        return render_to_response('registration/newuser_phase1.html',
                                  request, request.get_node('Q/Web/myesp'),
                                  {'form':form, 'site': Site.objects.get_current()})

def user_registration_phase2(request):
    """
    Registration view -- takes care of users who want to create a
    new account.
    """   
    if request.method == 'POST':
        return user_registration_validate(request)

    try:
        email = request.GET['email']
    except MultiValueDictKeyError:
        return HttpResponseRedirect(reverse("users.views.user_registration_phase1"))
    form = UserRegForm(initial={'email':email})
    return render_to_response('registration/newuser.html',
                              request, request.get_node('Q/Web/myesp'),{'form':form, 'email':email})



def activate_account(request):
    if not 'username' in request.GET or not 'key' in request.GET:
        raise ESPError(), "Invalid account activation information.  Please try again.  If this error persists, please contact us using the contact information on the top or bottom of this page."

    try:
        u = ESPUser.objects.get(username = request.GET['username'])
    except:
        raise ESPError(), "Invalid account username.  Please try again.  If this error persists, please contact us using the contact information on the top or bottom of this page."

    if not u.password.endswith("_%s" % request.GET['key']):
        return HttpResponseRedirect('/myesp/profile/')

    u.password = u.password[:-(len("_%s" % request.GET['key']))]
    u.is_active = True
    u.save()

    return HttpResponseRedirect('/myesp/profile/')

