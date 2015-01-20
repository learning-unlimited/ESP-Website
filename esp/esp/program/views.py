
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

from esp.web.util import render_to_response
from esp.qsd.models import QuasiStaticData
from esp.qsd.forms import QSDMoveForm, QSDBulkMoveForm
from esp.datatree.models import *
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
from esp.users.models import ESPUser, Permission, admin_required, ZipCode

from django.contrib.auth.decorators import login_required
from django.db.models.query import Q
from django.db.models import Min
from django.core.mail import mail_admins
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.http import HttpResponse
from django import forms

from esp.program.models import Program, TeacherBio, RegistrationType, ClassSection, StudentRegistration
from esp.program.forms import ProgramCreationForm, StatisticsQueryForm
from esp.program.setup import prepare_program, commit_program
from esp.program.controllers.confirmation import ConfirmationEmailController
from esp.program.modules.handlers.studentregcore import StudentRegCore
from esp.middleware import ESPError
from esp.accounting.controllers import ProgramAccountingController, IndividualAccountingController
from esp.mailman import create_list, load_list_settings, apply_list_settings, add_list_members
from esp.resources.models import ResourceType
from esp.tagdict.models import Tag
from django.conf import settings
import pickle
import operator
import simplejson as json
from collections import defaultdict
from decimal import Decimal

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


@login_required
def lottery_student_reg(request, program = None):
    """
    Serve the student reg page.

    This is just a static page;
    it gets all of its content from AJAX callbacks.
    """

    # First check whether the user is actually a student.
    if not request.user.isStudent():
        raise ESPError("You must be a student in order to access Splash student registration.", log=False)

    context = {}
    
    return render_to_response('program/modules/lotterystudentregmodule/student_reg.html', request, {})

@login_required
def lottery_student_reg_simple(request, program = None):
    """
    Serve the student reg page.

    This is just a static page;
    it gets all of its content from AJAX callbacks.
    """

    # First check whether the user is actually a student.
    if not request.user.isStudent():
        raise ESPError("You must be a student in order to access Splash student registration.", log=False)

    context = {}
    
    return render_to_response('program/modules/lotterystudentregmodule/student_reg_simple.html', request, {})


#@transaction.commit_manually
@login_required
def lsr_submit(request, program = None): 
    
    priority_limit = program.priorityLimit()

    data = json.loads(request.POST['json_data'])
    
    if priority_limit > 1: 
        return lsr_submit_HSSP(request, program, priority_limit, data) # temporary function. will merge the two later -jmoldow 05/31

    classes_interest = set()
    classes_no_interest = set()
    classes_flagged = set()
    classes_not_flagged = set()

    reg_priority, created = RegistrationType.objects.get_or_create(name="Priority/1", category="student")
    reg_interested, created = RegistrationType.objects.get_or_create(name="Interested", category="student",
                                                                     defaults={"description":"For lottery reg, a student would be interested in being placed into this class, but it isn't their first choice"})

    for reg_token, reg_status in data.iteritems():
        parts = reg_token.split('_')
        if parts[0] == 'flag':
            ## Flagged class
            flag, secid = parts
            if reg_status:
                classes_flagged.add(int(secid))
            else:
                classes_not_flagged.add(int(secid))
        else:
            secid = parts[0]
            if reg_status:
                classes_interest.add(int(secid))
                classes_no_interest.add(int(secid))

    errors = []

    already_flagged_sections = request.user.getSections(program=program, verbs=[reg_priority.name]).annotate(first_block=Min('meeting_times__start'))
    already_flagged_secids = set(int(x.id) for x in already_flagged_sections)
    
    flag_related_sections = classes_flagged | classes_not_flagged
    flagworthy_sections = ClassSection.objects.filter(id__in=flag_related_sections-already_flagged_secids).annotate(first_block=Min('meeting_times__start'))
    
    sections_by_block = defaultdict(list)
    sections_by_id = {}   
    for s in list(flagworthy_sections) + list(already_flagged_sections):
        sections_by_id[int(s.id)] = s
        print s.first_block
        if int(s.id) not in classes_not_flagged:
            sections_by_block[s.first_block].append(s)

    for val in sections_by_block.values():
        if len(val) > 1:
            errors.append({"text": "Can't flag two classes at the same time!", "cls_sections": [x.id for x in val], "block": val[0].firstBlockEvent().id, "flagged": True})

    if len(errors) == 0:
        for s_id in (already_flagged_secids - classes_flagged):
            sections_by_id[s_id].unpreregister_student(request.user, prereg_verb=reg_priority.name)
        for s_id in classes_flagged - already_flagged_secids:
            if not sections_by_id[s_id].preregister_student(request.user, prereg_verb=reg_priority.name, overridefull=True):
                errors.append({"text": "Unable to add flagged class", "cls_sections": [s_id], "emailcode": sections_by_id[s_id].emailcode(), "block": None, "flagged": True})

    already_interested_sections = request.user.getSections(program=program, verbs=[reg_interested.name])
    already_interested_secids = set(int(x.id) for x in already_interested_sections)
    interest_related_sections = classes_interest | classes_no_interest
    sections = ClassSection.objects.filter(id__in = (interest_related_sections - flag_related_sections - already_flagged_secids - already_interested_secids))

    ## No need to reset sections_by_id
    for s in list(sections) + list(already_interested_sections):
        sections_by_id[int(s.id)] = s

    for s_id in (already_interested_secids - classes_interest):
        sections_by_id[s_id].unpreregister_student(request.user, prereg_verb=reg_interested.name)
    for s_id in classes_interest - already_interested_secids:
        print s_id
        if not sections_by_id[s_id].preregister_student(request.user, prereg_verb=reg_interested.name, overridefull=True):
            errors.append({"text": "Unable to add interested class", "cls_sections": [s_id], "emailcode": sections_by_id[s_id].emailcode(), "block": None, "flagged": False})

    if len(errors) != 0:
        s = StringIO()
        print(errors, s)
        mail_admins('Error in class reg', s.getvalue(), fail_silently=True)

    cfe = ConfirmationEmailController()
    cfe.send_confirmation_email(request.user, program)

    return HttpResponse(json.dumps(errors), mimetype='application/json')


#@transaction.commit_manually
@login_required
def lsr_submit_HSSP(request, program, priority_limit, data):  # temporary function. will merge the two later -jmoldow 05/31
    
    classes_flagged = [set() for i in range(0,priority_limit+1)] # 1-indexed
    sections_by_block = [defaultdict(set) for i in range(0,priority_limit+1)] # 1-indexed - sections_by_block[i][block] is a set of classes that were given priority i in timeblock block. This should hopefully be a set of size 0 or 1.
    
    for section_id, (priority, block_id) in data.iteritems():
        section_id = int(section_id)
        priority = int(priority)
        block_id = int(block_id)
        classes_flagged[0].add(section_id)
        classes_flagged[priority].add(section_id)
        sections_by_block[priority][block_id].add(section_id)

    errors = []
    
    for i in range(1, priority_limit+1):
        for block in sections_by_block[i].keys():
            if len(sections_by_block[i][block]) > 1:
                errors.append({"text": "Can't flag two classes with the same priority at the same time!", "cls_sections": list(sections_by_block[i][block]), "block": block, "priority": i, "doubled_priority": True})
    
    if len(errors): 
        return HttpResponse(json.dumps(errors), mimetype='application/json')

    reg_priority = [(None,None)] + [RegistrationType.objects.get_or_create(name="Priority/"+str(i), category="student") for i in range(1,priority_limit+1)]
    reg_priority = [reg_priority[i][0] for i in range(0, priority_limit+1)] 
    
    allStudentRegistrations = StudentRegistration.valid_objects().filter(section__parent_class__parent_program=program, user=request.user)
    oldRegistrations = [] #[[] for i in range(0, priority_limit+1)] # 1-indexed for priority registrations, the 0-index is for interested registrations
    
    for i in range(1, priority_limit+1):
        oldRegistrations += [(oldRegistration, i) for oldRegistration in list(allStudentRegistrations.filter(relationship=reg_priority[i]).select_related(depth=3))]
    
    for (oldRegistration, priority) in oldRegistrations:
        if oldRegistration.section.id not in classes_flagged[0]:
            oldRegistration.expire()
            continue
        for i in range(1, priority_limit + 1):
            if oldRegistration.section.id in classes_flagged[i]:
                if i != priority:
                    oldRegistration.expire()
                elif i == priority:
                    classes_flagged[i].remove(oldRegistration.section.id)
                    classes_flagged[0].remove(oldRegistration.section.id)
                break
    
    flagworthy_sections = [None] + [ClassSection.objects.filter(id__in=classes_flagged[i]).select_related(depth=2).annotate(first_block=Min('meeting_times__start')) for i in range(1, priority_limit + 1)]
    
    for i in range(1, priority_limit + 1):
        for s in list(flagworthy_sections[i]):
            if not s.preregister_student(request.user, prereg_verb=reg_priority[i].name, overridefull=True):
                errors.append({"text": "Unable to add flagged class", "cls_sections": [s.id], "emailcode": s.emailcode(), "block": s.first_block, "flagged": True, "priority": i, "doubled_priority": False})

    if len(errors) != 0:
        s = StringIO()
        pprint(errors, s)
        mail_admins('Error in class reg', s.getvalue(), fail_silently=True)

    return HttpResponse(json.dumps(errors), mimetype='application/json')


def find_user(userstr):
    """
    Do a best-guess effort at finding a user based on a string identifying that user.
    The string may be a user ID, username, or some permuation of the user's real name.
    Will return a list of users if the string is not a username and more than one
    name approximately matches.
    Will return something that evaluates to False iff no matching users are found.
    """
    # First, is this a User ID?
    try:
        found_user = ESPUser.objects.get(id=int(userstr))
        return found_user
    except ValueError:
        pass # Well, that wasn't even an integer; can't be an ID
    except ESPUser.DoesNotExist:
        pass # Well, maybe it is an integer, but it's not a valid user ID.

    # Second, is it a username?
    try:
        found_user = ESPUser.objects.get(username=userstr)
        return found_user
    except ESPUser.DoesNotExist:
        pass # Well, not a username either.  Oh well.

    # Third, try e-mail?
    if '@' in userstr:  # but don't even bother hitting the DB if it doesn't even have an '@'
        found_users = ESPUser.objects.filter(email=userstr)
        if len(found_users) == 1:
            return found_users[0]
        elif len(found_users) > 1:
            return found_users
        # else, not an e-mail either.  Oh well.

    # Maybe it's a name?
    # Let's do some playing.

    # Is it multipart?        
    # If so, we don't know which parts got filed under first name and
    # which under last name.
    # So, try them all!
    # First, try for an exact match (ie., all parts of the firstname, lastname pair are somewhere in the given string)
    userstr_parts = userstr.split(' ')

    # First, try single-part, since it's easier
    if len(userstr_parts) == 1:
        found_users = ESPUser.objects.filter(Q(first_name__iexact=userstr) | Q(last_name__iexact=userstr))
        if len(found_users) == 1:
            return found_users[0]
        elif len(found_users) > 1:
            return found_users

        found_users = ESPUser.objects.filter(Q(first_name__icontains=userstr) | Q(last_name__icontains=userstr))
        if len(found_users) == 1:
            return found_users[0]
        elif len(found_users) > 1:
            return found_users
        
    q_list = []
    for i in xrange(len(userstr_parts) + 1):
        q_list.append( Q( first_name__iexact = ' '.join(userstr_parts[:i]), last_name__iexact = ' '.join(userstr_parts[i:]) ) )

    # Allow any of the above permutations
    q = reduce(operator.or_, q_list)
    found_users = ESPUser.objects.filter( q )
    if len(found_users) == 1:
        return found_users[0]
    elif len(found_users) > 1:
        return found_users
    # else, we found no one.  Oops.

    # Now, repeat the same thing, but with "contains" so we match some nicknames and whatnot
    
    q_list = []
    for i in xrange(len(userstr_parts)):
        q_list.append( Q( first_name__icontains = ' '.join(userstr_parts[:i]), last_name__icontains = ' '.join(userstr_parts[i:]) ) )
    # Allow any of the above permutations
    q = reduce(operator.or_, q_list)
    found_users = ESPUser.objects.filter( q )
    if len(found_users) == 1:
        return found_users[0]
    elif len(found_users) > 1:
        return found_users

    # lastly, try titles of courses a teacher has taught?
    found_users = ESPUser.objects.filter(classsubject__title__icontains=userstr).distinct()
    if len(found_users) == 1:
        return found_users[0]
    elif len(found_users) > 1:
        return found_users
    
    # else, we found no one.  Oops.

    # Well, we fail.  Sorry.
    return None

def isiterable(i):
    """ returns true iff i is iterable """
    try:
        for x in i:
            return True
    except TypeError:
        return False

@admin_required
def usersearch(request):
    """
    Given a string that's somehow associated with a user,
    do our best to find that user.
    Either redirect to that user's "userview" page, or
    display a list of users to pick from."""
    if not request.GET.has_key('userstr'):
        raise ESPError("You didn't specify a user to search for!", log=False)
                               
    userstr = request.GET['userstr']
    found_users = find_user(userstr)

    if not found_users:
        raise ESPError("No user found by that name!", log=False)

    if isiterable(found_users):
        return render_to_response('users/userview_search.html', request, { 'found_users': found_users })
    else:
        from urllib import urlencode
        return HttpResponseRedirect('/manage/userview?%s' % urlencode({'username': found_users.username}))

@admin_required
def userview(request):
    """ Render a template displaying all the information about the specified user """
    try:
        user = ESPUser.objects.get(username=request.GET['username'])
    except:
        raise ESPError("Sorry, can't find anyone with that username.", log=False)

    teacherbio = TeacherBio.getLastBio(user)
    if not teacherbio.picture:
        teacherbio.picture = 'images/not-available.jpg'
    
    from esp.users.forms.user_profile import StudentInfoForm
    
    if 'graduation_year' in request.GET:
        user.set_student_grad_year(request.GET['graduation_year'])
    
    change_grade_form = StudentInfoForm(user=user)
    if 'disabled' in change_grade_form.fields['graduation_year'].widget.attrs:
        del change_grade_form.fields['graduation_year'].widget.attrs['disabled']
    change_grade_form.fields['graduation_year'].initial = user.getYOG()
    change_grade_form.fields['graduation_year'].choices = filter(lambda choice: bool(choice[0]), change_grade_form.fields['graduation_year'].choices)
    
    context = {
        'user': user,
        'taught_classes' : user.getTaughtClasses().order_by('parent_program', 'id'),
        'enrolled_classes' : user.getEnrolledSections().order_by('parent_class__parent_program', 'id'),
        'taken_classes' : user.getSections().order_by('parent_class__parent_program', 'id'),
        'teacherbio': teacherbio,
        'domain': settings.SITE_INFO[1],
        'change_grade_form': change_grade_form,
        'printers': StudentRegCore.printer_names(),
    }
    return render_to_response("users/userview.html", request, context )


def deactivate_user(request):
    return activate_or_deactivate_user(request, activate=False)

def activate_user(request):
    return activate_or_deactivate_user(request, activate=True)

@admin_required
def activate_or_deactivate_user(request, activate):
    """Linked from the userview page."""
    if request.method != 'POST' or 'user_id' not in request.POST:
        return HttpResponseBadRequest('')
    else:
        users = ESPUser.objects.filter(id=request.POST['user_id'])
        if users.count() != 1:
            return HttpResponseBadRequest('')
        else:
            user = users[0]
            user.is_active = activate
            user.save()
            return HttpResponseRedirect('/manage/userview?username=%s' % user.username)


@admin_required
def manage_programs(request):
    #as admin required implies can administrate all programs now,
    admPrograms = Program.objects.all().order_by('-id')
    context = {'admPrograms': admPrograms,
               'user': request.user}
    return render_to_response('program/manage_programs.html', request, context)

@admin_required
def newprogram(request):
    template_prog = None
    template_prog_id = None
    if 'template_prog' in request.GET and (int(request.GET["template_prog"])) != 0:       # if user selects None which value is 0,so we need to check for 0.
       #try:
        template_prog_id = int(request.GET["template_prog"])
        tprogram = Program.objects.get(id=template_prog_id)
        template_prog = {}
        template_prog.update(tprogram.__dict__)
        del template_prog["id"]
        template_prog["program_type"] = tprogram.program_type
        template_prog["program_modules"] = tprogram.program_modules.all().values_list("id", flat=True)
        template_prog["class_categories"] = tprogram.class_categories.all().values_list("id", flat=True)
        '''
        As Program Name should be new for each new program created then it is better to not to show old program names in input box .
        template_prog["term"] = tprogram.anchor.name
        template_prog["term_friendly"] = tprogram.anchor.friendly_name
        '''
        
        student_reg_bits = list(Permission.objects.filter(permission_type__startswith='Student', program=template_prog_id).order_by('-start_date'))
        if len(student_reg_bits) > 0:
            newest_bit = student_reg_bits[0]
            oldest_bit = student_reg_bits[-1]

            template_prog["student_reg_start"] = oldest_bit.start_date
            template_prog["student_reg_end"] = newest_bit.end_date

        teacher_reg_bits = list(Permission.objects.filter(permission_type__startswith='Teacher', program=template_prog_id).order_by('-start_date'))
        if len(teacher_reg_bits) > 0:
            newest_bit = teacher_reg_bits[0]
            oldest_bit = teacher_reg_bits[-1]

            template_prog["teacher_reg_start"] = oldest_bit.start_date
            template_prog["teacher_reg_end"] = newest_bit.end_date

        pac = ProgramAccountingController(tprogram)
        line_items = pac.get_lineitemtypes(required_only=True).values('amount_dec')

        template_prog["base_cost"] = int(sum(x["amount_dec"] for x in line_items))
        template_prog["sibling_discount"] = tprogram.sibling_discount

    if 'checked' in request.GET:
        # Our form's anchor is wrong, because the form asks for the parent of the anchor that we really want.
        # Don't bother trying to fix the form; just re-set the anchor when we're done.
        context = pickle.loads(request.session['context_str'])
        pcf = ProgramCreationForm(context['prog_form_raw'])
        if pcf.is_valid():

            new_prog = pcf.save(commit = True)
            
            commit_program(new_prog, context['perms'], context['modules'], context['cost'], context['sibling_discount'])

            # Create the default resource types now
            default_restypes = Tag.getProgramTag('default_restypes', program=new_prog)
            if default_restypes:
                resource_type_labels = json.loads(default_restypes)
                resource_types = [ResourceType.get_or_create(x, new_prog) for x in resource_type_labels]
            
            #   Force all ProgramModuleObjs and their extensions to be created now
            new_prog.getModules()
            
            manage_url = '/manage/' + new_prog.url + '/resources'

            if settings.USE_MAILMAN and 'mailman_moderator' in settings.DEFAULT_EMAIL_ADDRESSES.keys():
                # While we're at it, create the program's mailing list
                mailing_list_name = "%s_%s" % (new_prog.program_type, new_prog.program_instance)
                teachers_list_name = "%s-%s" % (mailing_list_name, "teachers")
                students_list_name = "%s-%s" % (mailing_list_name, "students")

                create_list(students_list_name, settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'])
                create_list(teachers_list_name, settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'])

                load_list_settings(teachers_list_name, "lists/program_mailman.config")
                load_list_settings(students_list_name, "lists/program_mailman.config")
        
                apply_list_settings(teachers_list_name, {'owner': [settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'], new_prog.director_email]})
                apply_list_settings(students_list_name, {'owner': [settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'], new_prog.director_email]})

                if 'archive' in settings.DEFAULT_EMAIL_ADDRESSES.keys():
                    add_list_members(students_list_name, [new_prog.director_email, settings.DEFAULT_EMAIL_ADDRESSES['archive']])
                    add_list_members(teachers_list_name, [new_prog.director_email, settings.DEFAULT_EMAIL_ADDRESSES['archive']])
            

            return HttpResponseRedirect(manage_url)
        else:
            raise ESPError("Improper form data submitted.", log=False)
          

    #   If the form has been submitted, process it.
    if request.method == 'POST':
        form = ProgramCreationForm(request.POST)

        if form.is_valid():
            temp_prog = form.save(commit=False)
            perms, modules = prepare_program(temp_prog, form.cleaned_data)
            #   Save the form's raw data instead of the form itself, or its clean data.
            #   Unpacking of the data happens at the next step.

            context_pickled = pickle.dumps({'prog_form_raw': form.data, 'perms': perms, 'modules': modules, 'cost': form.cleaned_data['base_cost'], 'sibling_discount': form.cleaned_data['sibling_discount']})
            request.session['context_str'] = context_pickled
            
            return render_to_response('program/newprogram_review.html', request, {'prog': temp_prog, 'perms':perms, 'modules': modules})
        
    else:
        #   Otherwise, the default view is a blank form.
        if template_prog:
            form = ProgramCreationForm(template_prog)
        else:
            form = ProgramCreationForm()

    return render_to_response('program/newprogram.html', request, {'form': form, 'programs': Program.objects.all().order_by('-id'),'template_prog_id':template_prog_id})

@csrf_exempt
@login_required
def submit_transaction(request):
    #   We might also need to forward post variables to http://shopmitprd.mit.edu/controller/index.php?action=log_transaction
    
    if request.POST.has_key("decision") and request.POST["decision"] != "REJECT" and request.POST["decision"] != "ERROR":

        #   Figure out which user and program the payment are for.
        post_identifier = request.POST['req_merchant_defined_data1']
        post_amount = Decimal(request.POST['req_amount'])
        iac = IndividualAccountingController.from_identifier(post_identifier)

        #   Warn for possible duplicate payments
        prev_payments = iac.get_transfers().filter(line_item=iac.default_payments_lineitemtype())
        if prev_payments.count() > 0 and iac.amount_due() <= 0:
            from django.conf import settings
            recipient_list = [contact[1] for contact in settings.ADMINS]
            recipient_list.append(settings.DEFAULT_EMAIL_ADDRESSES['treasury']) 
            refs = 'Cybersource request ID: %s' % post_identifier

            subject = 'Possible Duplicate Postback/Payment'
            refs = 'User: %s (%d); Program: %s (%d)' % (iac.user.name(), iac.user.id, iac.program.niceName(), iac.program.id)
            refs += '\n\nPrevious payments\' Transfer IDs: ' + ( u', '.join([str(x.id) for x in prev_payments]) )

            # Send mail!
            send_mail('[ ESP CC ] ' + subject + ' by ' + iac.user.first_name + ' ' + iac.user.last_name, \
                  """%s Notification\n--------------------------------- \n\n%s\n\nUser: %s %s (%s)\n\nCardholder: %s, %s\n\nRequest: %s\n\n""" % \
                  (subject, refs, request.user.first_name, request.user.last_name, request.user.id, request.POST.get('req_bill_to_surname', '--'), request.POST.get('req_bill_to_forename', '--'), request) , \
                  settings.SERVER_EMAIL, recipient_list, True)

        #   Save the payment as a transfer in the database
        iac.submit_payment(post_amount, transaction_id=request.POST.get('transaction_id', ''))

        tl = 'learn'
        one, two = iac.program.url.split('/')
        destination = Tag.getProgramTag("cc_redirect", iac.program, default="confirmreg")

        if destination.startswith('/') or '//' in destination:
            pass
        else:
            # simple urls like 'confirmreg' are relative to the program
            destination = "/%s/%s/%s/%s" % (tl, one, two, destination)

        return HttpResponseRedirect(destination)

    return render_to_response( 'accounting/credit_rejected.html', request, {} )

# This really should go in qsd
@admin_required
def manage_pages(request):
    if request.method == 'POST':
        data = request.POST
        if request.GET['cmd'] == 'bulk_move':
            if data.has_key('confirm'):
                form = QSDBulkMoveForm(data)
                #   Handle submission of bulk move form
                if form.is_valid():
                    form.save_data()
                    return HttpResponseRedirect('/manage/pages')

            #   Create and display the form
            qsd_id_list = []
            for key in data.keys():
                if key.startswith('check_'):
                    qsd_id_list.append(int(key[6:]))
            if len(qsd_id_list) > 0:
                form = QSDBulkMoveForm()
                qsd_list = QuasiStaticData.objects.filter(id__in=qsd_id_list)
                common_path = form.load_data(qsd_list)
                if common_path:
                    return render_to_response('qsd/bulk_move.html', request, {'common_path': common_path, 'qsd_list': qsd_list, 'form': form})
        
        qsd = QuasiStaticData.objects.get(id=request.GET['id'])
        if request.GET['cmd'] == 'move':
            #   Handle submission of move form
            form = QSDMoveForm(data)
            if form.is_valid():
                form.save_data()
            else:
                return render_to_response('qsd/move.html', request, {'qsd': qsd, 'form': form})
        elif request.GET['cmd'] == 'delete':
            #   Mark as inactive all QSD pages matching the one with ID request.GET['id']
            if data['sure'] == 'True':
                all_qsds = QuasiStaticData.objects.filter(url=qsd.url, name=qsd.name)
                for q in all_qsds:
                    q.disabled = True
                    q.save()
        return HttpResponseRedirect('/manage/pages')

    elif request.GET.has_key('cmd'):
        qsd = QuasiStaticData.objects.get(id=request.GET['id'])
        if request.GET['cmd'] == 'delete':
            #   Show confirmation of deletion
            return render_to_response('qsd/delete_confirm.html', request, {'qsd': qsd})
        elif request.GET['cmd'] == 'undelete':
            #   Make all the QSDs enabled and return to viewing the list
            all_qsds = QuasiStaticData.objects.filter(url=qsd.url, name=qsd.name)
            for q in all_qsds:
                q.disabled = False
                q.save()
        elif request.GET['cmd'] == 'move':
            #   Show move form
            form = QSDMoveForm()
            form.load_data(qsd)
            return render_to_response('qsd/move.html', request, {'qsd': qsd, 'form': form})
            
    #   Show QSD listing 
    qsd_ids = []
    qsds = QuasiStaticData.objects.all().order_by('-create_date').values_list('id', 'url', 'name')
    seen_keys = set()
    for id, path, name in qsds:
        key = path, name
        if key not in seen_keys:
            qsd_ids.append(id)
            seen_keys.add(key)
    qsd_list = list(QuasiStaticData.objects.filter(id__in=qsd_ids))
    qsd_list.sort(key=lambda q: q.url)
    return render_to_response('qsd/list.html', request, {'qsd_list': qsd_list})
    
@admin_required
def flushcache(request):
    context = {}
    if request.POST:
        if request.POST.has_key("reason") and len(request.POST['reason']) > 5:
            reason = request.POST['reason']
            _cache = cache
            while hasattr(_cache, "_wrapped_cache"):
                _cache = _cache._wrapped_cache
            if hasattr(_cache, "clear"):
                _cache.clear()
                mail_admins("Cache Flushed on server '%s'!" % request.META['SERVER_NAME'], "The cache was flushed by %s!  The following reason was given:\n\n%s" % (request.user.username, reason))
                context['success'] = "Cache Cleared."
            else:
                context['error'] = "Error: This cache backend doesn't support the 'clear' method.  Sorry; you'll have to flush this one manually."
        else:
            context['error'] = "Sorry, that doesn't count as a reason."

    return render_to_response('admin/cache_flush.html', request, context)
                         

@admin_required
def statistics(request, program=None):

    def get_field_ids(form):
        field_ids = []
        #   Hack to make sure radio buttons are re-parsed correctly by Dojo
        for field_name in form.fields:
            if isinstance(form.fields[field_name].widget, forms.RadioSelect):
                for i in range(len(form.fields[field_name].choices)):
                    field_ids.append('%s_%d' % (field_name, i))
            else:
                field_ids.append(field_name)
        return field_ids
                    
    if request.method == 'POST':
        #   Hack for proper behavior when multiselect fields are hidden
        #   (they contain '' instead of simply being absent like they should)
        post_data = request.POST.copy()
        multiselect_fields = StatisticsQueryForm.get_multiselect_fields()
        for field_name in multiselect_fields:
            if field_name in post_data and post_data[field_name] == '':
                del post_data[field_name]
        
        form = StatisticsQueryForm(post_data, program=program)

        #   Handle case where all we want is a new form
        if 'update_form' in request.GET:
            form.hide_unwanted_fields()

            #   Return result
            context = {'form': form}
            context['clear_first'] = True
            context['field_ids'] = get_field_ids(form)
            result = {}
            result['statistics_form_contents_html'] = render_to_string('program/statistics/form.html', context)
            result['script'] = render_to_string('program/statistics/script.js', context)
            return HttpResponse(json.dumps(result), mimetype='application/json')
            
        if form.is_valid():
            #   A dictionary for template rendering the results of this query
            result_dict = {}
            #   A dictionary for template rendering the final response
            context = {}

            #   Get list of programs the query applies to
            programs = Program.objects.all()
            if not form.cleaned_data['program_type_all']:
                programs = programs.filter(url__startswith=form.cleaned_data['program_type'])
            if not form.cleaned_data['program_instance_all']:
                programs = programs.filter(url__in=form.cleaned_data['program_instances'])
            result_dict['programs'] = programs
            
            #   Get list of students the query applies to
            students_q = Q()
            for program in programs:
                for reg_type in form.cleaned_data['reg_types']:
                    students_q = students_q | program.students(QObjects=True)[reg_type]
                    
            #   Narrow down by school (perhaps not ideal results, but faster)
            if form.cleaned_data['school_query_type'] == 'name':
                students_q = students_q & (Q(studentinfo__school__icontains=form.cleaned_data['school_name']) | Q(studentinfo__k12school__name__icontains=form.cleaned_data['school_name']))
            elif form.cleaned_data['school_query_type'] == 'list':
                k12school_ids = []
                school_names = []
                for item in form.cleaned_data['school_multisel']:
                    if item.startswith('K12:'):
                        k12school_ids.append(int(item[4:]))
                    elif item.startwith('Sch:'):
                        school_names.append(item[4:])
                students_q = students_q & (Q(studentinfo__school__in=school_names) | Q(studentinfo__k12school__id__in=k12school_ids))
            
            #   Narrow down by Zip code, simply using the latest profile
            #   Note: it would be harder to track students better (i.e. zip code A in fall 2008, zip code B in fall 2009)
            if form.cleaned_data['zip_query_type'] == 'exact':
                students_q = students_q & Q(registrationprofile__contact_user__address_zip=form.cleaned_data['zip_code'], registrationprofile__most_recent_profile=True)
            elif form.cleaned_data['zip_query_type'] == 'partial':
                students_q = students_q & Q(registrationprofile__contact_user__address_zip__startswith=form.cleaned_data['zip_code_partial'], registrationprofile__most_recent_profile=True)
            elif form.cleaned_data['zip_query_type'] == 'distance':
                zipc = ZipCode.objects.get(zip_code=form.cleaned_data['zip_code'])
                zipcodes = zipc.close_zipcodes(form.cleaned_data['zip_code_distance'])
                students_q = students_q & Q(registrationprofile__contact_user__address_zip__in = zipcodes, registrationprofile__most_recent_profile=True)
                
            students = ESPUser.objects.filter(students_q).distinct()
            result_dict['num_students'] = students.count()
            profiles = [student.getLastProfile() for student in students]
            
            #   Accumulate desired information for selected query
            from esp.program import statistics as statistics_functions
            if hasattr(statistics_functions, form.cleaned_data['query']):
                context['result'] = getattr(statistics_functions, form.cleaned_data['query'])(form, programs, students, profiles, result_dict)
            else:
                context['result'] = 'Unsupported query'
                
            #   Generate response
            form.hide_unwanted_fields()
            context['form'] = form
            context['clear_first'] = False
            context['field_ids'] = get_field_ids(form)
            
            if request.is_ajax():
                result = {}
                result['result_html'] = context['result']
                result['script'] = render_to_string('program/statistics/script.js', context)
                return HttpResponse(json.dumps(result), mimetype='application/json')
            else:
                return render_to_response('program/statistics.html', request, context)
        else:
            #   Form was submitted but there are problems with it
            form.hide_unwanted_fields()
            context = {'form': form}
            context['clear_first'] = False
            context['field_ids'] = get_field_ids(form)
            if request.is_ajax():
                return HttpResponse(json.dumps(result), mimetype='application/json')
            else:
                return render_to_response('program/statistics.html', request, context)

    #   First request, form not yet submitted
    form = StatisticsQueryForm(program=program)
    form.hide_unwanted_fields()
    context = {'form': form}
    context['clear_first'] = False
    context['field_ids'] = get_field_ids(form)

    if request.is_ajax():
        return HttpResponse(json.dumps(context), mimetype='application/json')
    else:
        return render_to_response('program/statistics.html', request, context)

@admin_required
def template_preview(request):

    if 'template' in request.GET:
        template = request.GET['template']
    else:
        template = 'main.html'
        
    context = {}

    return render_to_response(template, request, context)
    
