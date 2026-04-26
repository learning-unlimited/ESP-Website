
from __future__ import absolute_import
import six
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""
from django.contrib.sites.models import Site
from esp.users.models import ESPUser, Permission
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.utils.datastructures import MultiValueDict
from django.template import loader
from django.views.generic.base import TemplateView
from esp.middleware.threadlocalrequest import AutoRequestContext as Context

import datetime
import re

from esp.dbmail.models import MessageRequest
from esp.web.models import NavBarCategory
from esp.utils.web import render_to_response, esp_context_stuff
from esp.web.views.navBar import makeNavBar
from esp.web.views.archives import archive_handlers
from esp.middleware import ESPError
from esp.web.forms.contact_form import ContactForm
from esp.tagdict.models import Tag
from esp.utils.no_autocookie import disable_csrf_cookie_update

from django.views.decorators.cache import cache_control
from django.conf import settings

@cache_control(max_age=180)
@disable_csrf_cookie_update
def home(request):
    #   Get navbars corresponding to the 'home' category
    nav_category, created = NavBarCategory.objects.get_or_create(name='home')
    context = {'navbar_list': makeNavBar('', nav_category)}
    return render_to_response('index.html', request, context)

def program(request, tl, one, two, module, extra = None):
    """ Return program-specific pages """
    from esp.program.models import Program

    if two == "current":
        try:
            programs = Program.objects.all()
            progs = [(program, program.dates()[-1]) for program in programs if program.program_type == one and len(program.dates()) > 0]
            two = sorted(progs, key=lambda x: x[1], reverse = True)[0][0].program_instance
        except:
            raise Http404("No current program of the type '" + one + "'.")
    try:
        prog = Program.by_prog_inst(one, two)
    except Program.DoesNotExist:
        raise Http404("Program not found.")

    setattr(request, "program", prog)
    setattr(request, "tl", tl)
    if extra:
        setattr(request, "module", "%s/%s" % (module, extra))
    else:
        setattr(request, "module", module)

    from esp.program.modules.base import ProgramModuleObj
    newResponse = ProgramModuleObj.findModule(request, tl, one, two, module, extra, prog)

    if newResponse:
        return newResponse

    raise Http404

@cache_control(max_age=180)
def public_email(request, email_id):
    email_req = MessageRequest.objects.filter(id=email_id, public=True)
    if email_req.count() == 1:
        return render_to_response('public_email.html', request, {'email_req': email_req[0]})
    else:
        raise ESPError('Invalid email id.', log=False)

def archives(request, selection, category = None, options = None):
    """ Return a page with class archives """

    sortparams = []
    if request.POST and 'newparam' in request.POST:
        if request.POST['newparam']:
            sortparams.append(request.POST['newparam'])
        for key in request.POST:
            if key.startswith('sortparam') and request.POST[key] != request.POST['newparam']: sortparams.append(request.POST[key])
    #    The selection variable is the type of data they want to see:
    #    classes, programs, teachers, etc.
    if selection in archive_handlers:
        return archive_handlers[selection](request, category, options, sortparams)

    return render_to_response('users/construction', request, {})

class DefaultQSDView(TemplateView):
    def get_context_data(self, **kwargs):
        return esp_context_stuff()

class FAQView(DefaultQSDView):
    template_name = "faq.html"

class ContactUsView(DefaultQSDView):
    template_name = "contact_qsd.html"

def contact(request, section='esp'):
    """
    This view should take an email and post to those people.
    """
    from esp.dbmail.models import send_mail
    # if not set up, immediately redirect
    if not Tag.getBooleanTag('contact_form_enabled'):
        return HttpResponseRedirect("/contact.html")

    if 'success' in request.GET:
        return render_to_response('contact_success.html', request, {})

    if request.method == 'POST':
        form = ContactForm(request.POST)
        SUBJECT_PREPEND = '[webform]'
        domain = Site.objects.get_current().domain
        ok_to_send = True

        if form.is_valid():
            anonymous = form.cleaned_data['anonymous']

            to_email = []
            bcc = []
            usernames = []
            logged_in_as = ""
            user_agent_str = request.META.get('HTTP_USER_AGENT', "(not specified)")

            email = form.cleaned_data['sender']
            if not anonymous:
                logged_in_as = request.user.username if hasattr(request, 'user') and request.user.is_authenticated() else "(not authenticated)"
                usernames = ESPUser.objects.filter(email__iexact = email).values_list('username', flat = True)

                if usernames and not form.cleaned_data['decline_password_recovery']:
                    m = 'password|account|log( ?)in'
                    if re.search(m, form.cleaned_data['message'].lower()) or re.search(m, form.cleaned_data['subject'].lower()):
                        # Ask if they want a password recovery before sending.
                        ok_to_send = False
                        # If they submit again, don't ask a second time.
                        form.data = MultiValueDict(form.data)
                        form.data['decline_password_recovery'] = True

                if len(form.cleaned_data['name'].strip()) > 0:
                    email = ESPUser.email_sendto_address(email, form.cleaned_data['name'])

                if form.cleaned_data['cc_myself']:
                    to_email.append(email)
            else:
                if form.cleaned_data['cc_myself']:
                    bcc.append(email)

                email = settings.CONTACTFORM_EMAIL_ADDRESSES[form.cleaned_data['topic'].lower()]

            to_email.append(settings.CONTACTFORM_EMAIL_ADDRESSES[form.cleaned_data['topic'].lower()])

            if ok_to_send:
                t = loader.get_template('email/comment')

                context = {
                    'form': form,
                    'domain': domain,
                    'usernames': usernames,
                    'logged_in_as': logged_in_as,
                    'user_agent_str': user_agent_str,
                    'anonymous': anonymous
                }
                msgtext = t.render(Context(context))

                send_mail(SUBJECT_PREPEND + ' '+ form.cleaned_data['subject'],
                    msgtext,
                    email, to_email, fail_silently = True, bcc = bcc)

                return HttpResponseRedirect(request.path + '?success')

    else:
        initial = {}
        if request.user.is_authenticated():
            initial['sender'] = request.user.email
            initial['name']   = request.user.first_name + ' '+request.user.last_name

        if section != '':
            initial['topic'] = section.lower()

        form = ContactForm(initial = initial)

    return render_to_response('contact.html', request, {'contact_form': form})


def registration_redirect(request):
    """ A view which returns:
        - A redirect to the currently open registration if exactly one registration is open
        - A list of open registration links otherwise
    """
    from esp.users.models import ESPUser
    from esp.program.models import Program

    user = request.user

    # prepare the rendered page so it points them to open student/teacher reg's
    ctxt = {}
    userrole = {}

    if user.isTeacher():
        userrole['name'] = 'Teacher'
        userrole['base'] = 'teach'
        userrole['reg'] = 'teacherreg'
        # first check for which programs they can still create a class
        progs = list(set(Permission.program_by_perm(user, 'Teacher/Classes/Create/Class')) | set(Permission.program_by_perm(user, 'Teacher/Classes/Create/OpenClass')))
        # then check for which programs they have already registered a class
        for prog in user.getTaughtPrograms():
            # only include the program if it hasn't finished yet
            if prog not in progs and prog.datetime_range()[1] > datetime.datetime.now():
                progs.append(prog)
    elif user.isVolunteer():
        userrole['name'] = 'Volunteer'
        userrole['base'] = 'volunteer'
        userrole['reg'] = 'signup'
        progs = list(Permission.program_by_perm(user, 'Volunteer/Signup'))
    elif user.isStudent():
        userrole['name'] = 'Student'
        userrole['base'] = 'learn'
        userrole['reg'] = 'studentreg'
        # first check for which program they can still register for a class
        user_grade = user.getGrade()
        progs = list(Permission.program_by_perm(user, 'Student/Classes').filter(grade_min__lte=user_grade, grade_max__gte=user_grade))
        # then check for which programs they have already registered for a class
        for prog in user.getLearntPrograms():
            # only include the program if it hasn't finished yet
            if prog not in progs and prog.datetime_range()[1] > datetime.datetime.now():
                progs.append(prog)
    else:
        progs = []

    ctxt['userrole'] = userrole

    #   If we have 1 program, automatically redirect to registration for that program.
    #   Most chapters will want this, but it can be disabled by a Tag.
    if len(progs) == 1 and Tag.getBooleanTag('automatic_registration_redirect'):
        ctxt['prog'] = progs[0]
        return HttpResponseRedirect(six.u('/%s/%s/%s') % (userrole['base'], progs[0].getUrlBase(), userrole['reg']))
    else:
        if len(progs) > 0:
            #   Sort available programs newest first
            progs.sort(key=lambda x: -x.id)
            ctxt['progs'] = progs
            ctxt['prog'] = progs[0]
        return render_to_response('users/profile_complete.html', request, ctxt)

def set_csrf_token(request):
    # Call get_token to set the CSRF cookie
    from django.middleware.csrf import get_token
    get_token(request)
    return HttpResponse('') # Return the minimum possible
