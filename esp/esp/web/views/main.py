
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
from esp.qsd.views import qsd
from django.core.exceptions import PermissionDenied
from django.contrib.sites.models import Site
from esp.program.modules.base import LOGIN_URL
from django.contrib.auth import REDIRECT_FIELD_NAME
from esp.users.models import ESPUser, Permission
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.utils.datastructures import MultiValueDict
from django.template import loader
from esp.middleware.threadlocalrequest import AutoRequestContext as Context
from urllib import quote

from Cookie import SimpleCookie

import datetime
import re
import json

from esp.dbmail.models import MessageRequest
from esp.web.models import NavBarCategory
from esp.utils.web import render_to_response
from esp.web.views.navBar import makeNavBar
from esp.web.views.archives import archive_handlers
from esp.middleware import ESPError
from esp.web.forms.contact_form import ContactForm
from esp.tagdict.models import Tag
from esp.utils.no_autocookie import disable_csrf_cookie_update
from esp.utils.query_utils import nest_Q

from django.views.decorators.cache import cache_control
from django.core.mail import mail_admins
from django.conf import settings

from django.views.decorators.csrf import csrf_exempt

from pprint import pprint

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

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

def contact(request, section='esp'):
    """
    This view should take an email and post to those people.
    """
    from django.core.mail import send_mail

    if 'success' in request.GET:
        return render_to_response('contact_success.html', request, {})

    if request.method == 'POST':
        form = ContactForm(request.POST)
        SUBJECT_PREPEND = '[webform]'
        domain = Site.objects.get_current().domain
        ok_to_send = True

        if form.is_valid():

            to_email = []
            usernames = []
            logged_in_as = request.user.username if hasattr(request, 'user') and request.user.is_authenticated() else "(not authenticated)"
            user_agent_str = request.META.get('HTTP_USER_AGENT', "(not specified)")

            email = form.cleaned_data['sender']
            usernames = ESPUser.objects.filter(email__iexact = email).values_list('username', flat = True)

            if usernames and not form.cleaned_data['decline_password_recovery']:
                m = 'password|account|log( ?)in'
                if re.search(m, form.cleaned_data['message'].lower()) or re.search(m, form.cleaned_data['subject'].lower()):
                    # Ask if they want a password recovery before sending.
                    ok_to_send = False
                    # If they submit again, don't ask a second time.
                    form.data = MultiValueDict(form.data)
                    form.data['decline_password_recovery'] = True

            if form.cleaned_data['cc_myself']:
                to_email.append(email)

            to_email.append(settings.CONTACTFORM_EMAIL_ADDRESSES[form.cleaned_data['topic'].lower()])

            if len(form.cleaned_data['name'].strip()) > 0:
                email = '%s <%s>' % (form.cleaned_data['name'], email)

            if ok_to_send:
                t = loader.get_template('email/comment')

                context = {
                    'form': form,
                    'domain': domain,
                    'usernames': usernames,
                    'logged_in_as': logged_in_as,
                    'user_agent_str': user_agent_str
                }
                msgtext = t.render(Context(context))

                send_mail(SUBJECT_PREPEND + ' '+ form.cleaned_data['subject'],
                    msgtext,
                    email, to_email, fail_silently = True)

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
    regperm = None
    if user.isStudent():
        userrole['name'] = 'Student'
        userrole['base'] = 'learn'
        userrole['reg'] = 'studentreg'
        regperm = 'Student/Classes'
    elif user.isTeacher():
        userrole['name'] = 'Teacher'
        userrole['base'] = 'teach'
        userrole['reg'] = 'teacherreg'
        regperm = 'Teacher/Classes'
    ctxt['userrole'] = userrole

    if regperm:
        progs = list(Permission.program_by_perm(user,regperm))
    else:
        progs = []

    #   If we have 1 program, automatically redirect to registration for that program.
    #   Most chapters will want this, but it can be disabled by a Tag.
    if len(progs) == 1 and Tag.getBooleanTag('automatic_registration_redirect'):
        ctxt['prog'] = progs[0]
        return HttpResponseRedirect(u'/%s/%s/%s' % (userrole['base'], progs[0].getUrlBase(), userrole['reg']))
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
