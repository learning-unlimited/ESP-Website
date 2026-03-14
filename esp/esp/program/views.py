
from functools import lru_cache, reduce
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

import logging
logger = logging.getLogger(__name__)
import traceback
import os
from operator import __or__ as OR
from pprint import pprint

from argcache import cache_function

from esp.utils.web import render_to_response
from esp.qsd.models import QuasiStaticData
from esp.qsd.forms import QSDMoveForm, QSDBulkMoveForm
from django.http import HttpResponseRedirect, HttpResponseBadRequest

from django.core.mail import send_mail

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site
from django.db.models.query import Q
from django.db.models import Min
from django.db import transaction
from django.core.mail import mail_admins
from django.core.cache import cache
from django.urls import reverse
from django.forms.models import model_to_dict
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.http import HttpResponse
from django import forms

from esp.program.modules.module_ext import ClassRegModuleInfo, StudentClassRegModuleInfo
from esp.program.models import Program, TeacherBio, RegistrationType, ClassSection, StudentRegistration, VolunteerOffer, RegistrationProfile, ClassCategories, ClassFlagType, StudentSubjectInterest
from esp.program.forms import ProgramCreationForm, StatisticsQueryForm, TagSettingsForm, CategoryForm, FlagTypeForm, RecordTypeForm, RedirectForm, PlainRedirectForm
from esp.program.setup import prepare_program, commit_program
from esp.program.controllers.confirmation import ConfirmationEmailController
from esp.program.controllers.studentclassregmodule import RegistrationTypeController as RTC
from esp.program.modules.handlers.studentregcore import StudentRegCore
from esp.program.modules.handlers.commmodule import CommModule
from esp.users.models import ESPUser, Permission, admin_required, ZipCode, UserAvailability, GradeChangeRequest, RecordType
from esp.middleware import ESPError
from esp.accounting.controllers import ProgramAccountingController, IndividualAccountingController
from esp.accounting.models import CybersourcePostback
from esp.dbmail.models import MessageRequest, TextOfEmail, PlainRedirect
from esp.mailman import create_list, load_list_settings, apply_list_settings, add_list_members
from esp.resources.models import ResourceType
from esp.tagdict.models import Tag
from django.conf import settings

import re
import pickle
import operator
import json
from docutils.core import publish_parts
import datetime
from collections import defaultdict
from decimal import Decimal
from reversion import revisions as reversion

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

# ---------------------------------------------------------------------------
# Documentation viewer helpers
# ---------------------------------------------------------------------------

# Absolute path to docs/admin/ (three levels above this file:
# views.py -> program -> esp -> esp -> devsite/docs/admin)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_ADMIN_ROOT = os.path.normpath(
    os.path.join(_THIS_DIR, '..', '..', '..', 'docs', 'admin')
)

import bleach
import mimetypes


def _rst_to_html(rst_text):
    """Convert a reStructuredText string to an HTML body fragment safely."""
    parts = publish_parts(
        source=rst_text,
        writer_name='html',
        settings_overrides={
            'halt_level': 5,
            'report_level': 5,
            'file_insertion_enabled': False,
            'raw_enabled': False,
        },
    )
    raw_html = parts['body']

    # Sanitize using bleach to prevent XSS (CodeQL robustness)
    allowed_tags = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a', 'img', 'ul', 'ol', 'li',
        'strong', 'em', 'code', 'pre', 'blockquote', 'table', 'tr', 'td', 'th',
        'tbody', 'thead', 'span', 'div', 'br', 'hr', 'dl', 'dt', 'dd', 'tt'
    ]
    allowed_attributes = {
        '*': ['class', 'id', 'title'],
        'a': ['href', 'target'],
        'img': ['src', 'alt', 'width', 'height'],
    }
    allowed_protocols = ['http', 'https', 'mailto']

    return bleach.clean(
        raw_html,
        tags=allowed_tags,
        attributes=allowed_attributes,
        protocols=allowed_protocols
    )


def _extract_rst_title(fpath):
    """Return the RST document title from a file, or None."""
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            rst_text = f.read()

        from docutils.core import publish_doctree
        # Disable file insertion during parsing for safety
        doctree = publish_doctree(
            source=rst_text,
            settings_overrides={'file_insertion_enabled': False, 'raw_enabled': False}
        )
        from docutils import nodes
        titles = doctree.traverse(nodes.title)
        if titles:
            return titles[0].astext()
        return None
    except Exception:
        return None


@lru_cache(maxsize=1)
def _docs_nav():
    """Return a list of {'title', 'url_path'} dicts for the docs sidebar."""

    nav = []
    try:
        filenames = sorted(os.listdir(DOCS_ADMIN_ROOT))
    except OSError:
        return nav

    for fname in filenames:
        if not fname.endswith('.rst'):
            continue
        # Skip the admin README — the index page serves as the overview
        if fname == 'README.rst':
            continue
        fpath = os.path.join(DOCS_ADMIN_ROOT, fname)
        fallback = fname.replace('.rst', '').replace('_', ' ').title()
        title = _extract_rst_title(fpath) or fallback
        nav.append({
            'title': title,
            'url_path': fname,
        })
    # Release notes index
    nav.append({
        'title': 'Release Notes',
        'url_path': 'releases/README.rst',
    })
    return nav



def _latest_release():
    """Return (label, html) for the most recent release notes."""
    releases_dir = os.path.join(DOCS_ADMIN_ROOT, 'releases')
    try:
        subdirs = [
            d for d in os.listdir(releases_dir)
            if os.path.isdir(os.path.join(releases_dir, d)) and d.isdigit()
        ]
    except OSError:
        return None, None
    if not subdirs:
        return None, None
    latest = str(max(int(d) for d in subdirs))
    rst_path = os.path.join(releases_dir, latest, 'README.rst')
    try:
        with open(rst_path, 'r', encoding='utf-8') as f:
            rst_text = f.read()
    except OSError:
        return None, None
    # Extract title line for the label
    label = 'SR{0}'.format(latest)
    lines = rst_text.splitlines()
    for line in lines:
        line = line.strip()
        if line and not set(line).issubset(set('= ')):
            label = line.strip()
            break

    # Truncate to give a preview (skip table of contents, stop at Changelog or after 15 lines)
    preview_lines = []
    skip_contents = False

    for i, line in enumerate(lines):
        if line.startswith('.. contents::'):
            skip_contents = True
            continue
        if skip_contents and line.startswith('      '): # skip indented TOC items
            continue
        else:
            skip_contents = False

        if line.startswith('Changelog') or len(preview_lines) >= 15:
            break
        preview_lines.append(line)

    preview_lines.append("")
    preview_lines.append("`\u2192 Read the full %s </manage/docs/releases/%s/README.rst>`__" % (label, latest))

    return label, _rst_to_html("\n".join(preview_lines))

# ---------------------------------------------------------------------------

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

@transaction.atomic
@login_required
def lsr_submit(request, program=None):

    priority_limit = program.priorityLimit()

    json_data = request.POST.get('json_data')
    if not json_data:
        return HttpResponse(json.dumps([{"text": "Missing required data"}]), status=400, content_type='application/json')
    try:
        data = json.loads(json_data)
    except (ValueError, TypeError):
        return HttpResponse(json.dumps([{"text": "Invalid JSON data"}]), status=400, content_type='application/json')

    if priority_limit > 1:
        return lsr_submit_HSSP(request, program, priority_limit, data) # temporary function. will merge the two later -jmoldow 05/31

    classes_interest = set()
    classes_no_interest = set()
    classes_flagged = set()
    classes_not_flagged = set()

    reg_priority, created = RegistrationType.objects.get_or_create(name="Priority/1", category="student")
    reg_interested, created = RegistrationType.objects.get_or_create(name="Interested", category="student",
                                                                     defaults={"description":"For lottery reg, a student would be interested in being placed into this class, but it isn't their first choice"})

    for reg_token, reg_status in data.items():
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
            else:
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
        if int(s.id) not in classes_not_flagged:
            sections_by_block[s.first_block].append(s)

    for val in sections_by_block.values():
        if len(val) > 1:
            errors.append({"text": "Can't flag two classes at the same time!", "cls_sections": [x.id for x in val], "block": val[0].firstBlockEvent().id, "flagged": True})

    if len(errors) == 0:
        for s_id in (already_flagged_secids - classes_flagged):
            sections_by_id[s_id].unpreregister_student(request.user, prereg_verbs=[reg_priority.name])
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
        sections_by_id[s_id].unpreregister_student(request.user, prereg_verbs=[reg_interested.name])
    for s_id in classes_interest - already_interested_secids:
        if not sections_by_id[s_id].preregister_student(request.user, prereg_verb=reg_interested.name, overridefull=True):
            errors.append({"text": "Unable to add interested class", "cls_sections": [s_id], "emailcode": sections_by_id[s_id].emailcode(), "block": None, "flagged": False})

    if len(errors) != 0:
        mail_admins('Error in class reg', str(errors), fail_silently=True)

    cfe = ConfirmationEmailController()
    cfe.send_confirmation_email(request.user, program)

    return HttpResponse(json.dumps(errors), content_type='application/json')

@transaction.atomic
@login_required
def lsr_submit_HSSP(request, program, priority_limit, data):  # temporary function. will merge the two later -jmoldow 05/31

    classes_flagged = [set() for i in range(0, priority_limit+1)] # 1-indexed
    sections_by_block = [defaultdict(set) for i in range(0, priority_limit+1)] # 1-indexed - sections_by_block[i][block] is a set of classes that were given priority i in timeblock block. This should hopefully be a set of size 0 or 1.

    errors = []

    for section_id, value in data.items():
        try:
            priority, block_id = value
        except (ValueError, TypeError):
            errors.append({"text": "Invalid data structure for class registration", "cls_sections": []})
            continue

        try:
            section_id = int(section_id)
            priority = int(priority)
            block_id = int(block_id)
        except (ValueError, TypeError):
            errors.append({"text": "Invalid data format", "cls_sections": []})
            continue

        classes_flagged[0].add(section_id)
        classes_flagged[priority].add(section_id)
        sections_by_block[priority][block_id].add(section_id)

    for i in range(1, priority_limit+1):
        for block in sections_by_block[i].keys():
            if len(sections_by_block[i][block]) > 1:
                errors.append({"text": "Can't flag two classes with the same priority at the same time!", "cls_sections": list(sections_by_block[i][block]), "block": block, "priority": i, "doubled_priority": True})

    if len(errors):
        return HttpResponse(json.dumps(errors), content_type='application/json')

    reg_priority = [(None, None)] + [RegistrationType.objects.get_or_create(name="Priority/"+str(i), category="student") for i in range(1, priority_limit+1)]
    reg_priority = [reg_priority[i][0] for i in range(0, priority_limit+1)]

    allStudentRegistrations = StudentRegistration.valid_objects().filter(section__parent_class__parent_program=program, user=request.user)
    oldRegistrations = [] #[[] for i in range(0, priority_limit+1)] # 1-indexed for priority registrations, the 0-index is for interested registrations

    for i in range(1, priority_limit+1):
        oldRegistrations += [(oldRegistration, i) for oldRegistration in list(allStudentRegistrations.filter(relationship=reg_priority[i]))]

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

    flagworthy_sections = [None] + [ClassSection.objects.filter(id__in=classes_flagged[i]).annotate(first_block=Min('meeting_times__start')) for i in range(1, priority_limit + 1)]

    for i in range(1, priority_limit + 1):
        for s in list(flagworthy_sections[i]):
            if not s.preregister_student(request.user, prereg_verb=reg_priority[i].name, overridefull=True):
                errors.append({"text": "Unable to add flagged class", "cls_sections": [s.id], "emailcode": s.emailcode(), "block": s.first_block, "flagged": True, "priority": i, "doubled_priority": False})

    if len(errors) != 0:
        s = StringIO()
        pprint(errors, s)
        mail_admins('Error in class reg', s.getvalue(), fail_silently=True)

    return HttpResponse(json.dumps(errors), content_type='application/json')

def find_user(userstr):
    """
    Do a best-guess effort at finding a user based on a string identifying that user.
    The string may be a user ID, username, or some permutation of the user's real name.
    Will return a list of users if the string is not a username and more than one
    name approximately matches.
    Will return something that evaluates to False if no matching users are found.

    returns: queryset containing ESPUser instances.
    """

    userstr = userstr.strip()
    userstr_parts = [part.strip() for part in userstr.split(' ') if part]

    if len(userstr_parts) == 2 and \
       re.match("\A\(\d\d\d\)\Z", userstr_parts[0]) and \
       re.match("[^A-Za-z]*", userstr_parts[1]):
        # HACK: coerce ["(555)", "555-5555"] to ["(555)555-5555"] so that the
        # first branch of the if statement gets taken
        userstr_parts = ["".join(userstr_parts)]

    # Single search token, could be username, id or email
    # worth noting that a username may be an integer or an email so we will just check them all
    found_users = None
    if len(userstr_parts) == 1:
        # Try username?
        user_q = Q(username__iexact=userstr)
        # Try user id
        if userstr.isnumeric():
            user_q = user_q | Q(id=userstr)
        # Try email
        if '@' in userstr:  # Don't even bother hitting the DB if it doesn't even have an '@'
            user_q = user_q | Q(email__iexact=userstr)
            user_q = user_q | Q(contactinfo__e_mail__iexact=userstr)  # Search parent contact info, too
        # Try phone
        cleaned = userstr
        for char in "-.() ":
            cleaned = cleaned.replace(char, "")
        if cleaned.isnumeric() and len(cleaned) == 10:
            formatted = "%s%s%s-%s%s%s-%s%s%s%s" % tuple(cleaned)
            user_q = user_q | Q(contactinfo__phone_day=formatted) | Q(contactinfo__phone_cell=formatted)
        # Try name (including parent/emergency contact)
        user_q = user_q | (Q(first_name__icontains=userstr) | Q(last_name__icontains=userstr))
        user_q = user_q | (Q(contactinfo__first_name__icontains=userstr) | Q(contactinfo__last_name__icontains=userstr))
        found_users = ESPUser.objects.filter(user_q).distinct()
    else:
        q_list = []
        for i in range(len(userstr_parts)):
            q_list.append( Q( first_name__icontains = ' '.join(userstr_parts[:i]), last_name__icontains = ' '.join(userstr_parts[i:]) ) )
            q_list.append( Q( contactinfo__first_name__icontains = ' '.join(userstr_parts[:i]), contactinfo__last_name__icontains = ' '.join(userstr_parts[i:]) ) )
        # Allow any of the above permutations
        q = reduce(operator.or_, q_list)
        found_users = ESPUser.objects.filter( q ).distinct()

    #if the previous search attempt failed, try titles of courses a teacher has taught?
    if not found_users.exists():
        found_users = ESPUser.objects.filter(classsubject__title__icontains=userstr).distinct()

    return found_users

@admin_required
def usersearch(request):
    """
    Given a string that's somehow associated with a user,
    do our best to find that user.
    Either redirect to that user's "userview" page, or
    display a list of users to pick from."""
    if not request.GET.get('userstr'):
        raise ESPError("You didn't specify a user to search for!", log=False)

    userstr = request.GET['userstr']
    found_users = find_user(userstr)
    num_users = found_users.count()

    if num_users == 1:
        from urllib.parse import urlencode
        return HttpResponseRedirect('/manage/userview?%s' % urlencode({'username': found_users[0].username}))
    elif num_users > 1:
        found_users = found_users.all()
        sorted_users = sorted(found_users, key=lambda x: x.get_last_program_with_profile().dates()[0] if x.get_last_program_with_profile() and x.get_last_program_with_profile().dates() else datetime.date(datetime.MINYEAR, 1, 1), reverse=True)
        return render_to_response('users/userview_search.html', request, { 'found_users': sorted_users })
    else:
        raise ESPError("No user found by that name! Searched for `{}`".format(userstr), log=False)

@admin_required
def userview(request):
    """ Render a template displaying all the information about the specified user """
    try:
        user = ESPUser.objects.get(username=request.GET['username'])
    except ESPUser.DoesNotExist:
        raise ESPError("Sorry, can't find anyone with that username.", log=False)

    if 'program' in request.GET:
        try:
            program = Program.objects.get(id=request.GET['program'])
        except Program.DoesNotExist:
            raise ESPError("Sorry, can't find that program.", log=False)
    else:
        program = user.get_last_program_with_profile()

    learn_modules = []
    teach_modules = []
    learn_records = []
    teach_records = []
    if program:
        profile = RegistrationProfile.getLastForProgram(user, program)
        if user.isStudent():
            learn_modules = program.getModules(user, 'learn')
            learn_records = StudentRegCore.get_reg_records(user, program, 'learn')
        if user.isTeacher():
            teach_modules = program.getModules(user, 'teach')
            teach_records = StudentRegCore.get_reg_records(user, program, 'teach')
    else:
        profile = user.getLastProfile()

    teacherbio = TeacherBio.getLastBio(user)
    if not teacherbio.picture:
        teacherbio.picture = 'images/not-available.jpg'

    from esp.users.forms.user_profile import StudentInfoForm

    if 'approve_request' in request.GET:
        gcrs = GradeChangeRequest.objects.filter(id=request.GET['approve_request'])
        if gcrs.count() == 1:
            gcr = gcrs[0]
            gcr.approved = True
            gcr.acknowledged_by = request.user
            gcr.save()
    if 'reject_request' in request.GET:
        gcrs = GradeChangeRequest.objects.filter(id=request.GET['reject_request'])
        if gcrs.count() == 1:
            gcr = gcrs[0]
            gcr.approved = False
            gcr.acknowledged_by = request.user
            gcr.save()

    if 'graduation_year' in request.GET:
        user.set_student_grad_year(request.GET['graduation_year'])

    change_grade_form = StudentInfoForm(user=user)
    if 'disabled' in change_grade_form.fields['graduation_year'].widget.attrs:
        del change_grade_form.fields['graduation_year'].widget.attrs['disabled']
    change_grade_form.fields['graduation_year'].initial = user.getYOG()
    change_grade_form.fields['graduation_year'].choices = [choice for choice in change_grade_form.fields['graduation_year'].choices if bool(choice[0])]

    # Split enrolled sections: those from the selected program vs. all others
    all_enrolled = user.getEnrolledSections().order_by('parent_class__parent_program', 'id')
    if program:
        program_enrolled = all_enrolled.filter(parent_class__parent_program=program)
        other_enrolled = all_enrolled.exclude(parent_class__parent_program=program)
    else:
        program_enrolled = all_enrolled
        other_enrolled = all_enrolled.none()

    # Split taken/applied sections the same way
    all_taken = user.getSections().order_by('parent_class__parent_program', 'id')
    if program:
        program_taken = all_taken.filter(parent_class__parent_program=program)
        other_taken = all_taken.exclude(parent_class__parent_program=program)
    else:
        program_taken = all_taken
        other_taken = all_taken.none()

    # Get StudentSubjectInterests (starred classes) for this user
    starred_classes = []
    if program:
        # If a specific program is selected, filter by that program
        starred_classes = StudentSubjectInterest.objects.filter(user=user, subject__parent_program=program)
    else:
        # If no specific program, show all starred classes for this user
        starred_classes = StudentSubjectInterest.objects.filter(user=user)

    context = {
        'user': user,
        'taught_classes': user.getTaughtClasses(include_rejected = True).order_by('parent_program', 'id'),
        'program_enrolled': program_enrolled,
        'other_enrolled': other_enrolled,
        'program_taken': program_taken,
        'other_taken': other_taken,
        'starred_classes': starred_classes,
        'teacherbio': teacherbio,
        'domain': settings.SITE_INFO[1],
        'change_grade_form': change_grade_form,
        'printers': StudentRegCore.printer_names(),
        'all_programs': Program.objects.all().order_by('-id'),
        'program': program,
        'learn_modules': learn_modules,
        'teach_modules': teach_modules,
        'learn_records': learn_records,
        'teach_records': teach_records,
        'profile': profile,
        'volunteer': VolunteerOffer.objects.filter(request__program = program, user = user).exists(),
        'avail_set': UserAvailability.objects.filter(event__program = program, user = user).exists(),
        'grade_change_requests': user.requesting_student_set.filter(approved=None),
    }
    return render_to_response("users/userview.html", request, context )

def deactivate_user(request):
    return activate_or_deactivate_user(request, activate=False)

def activate_user(request):
    return activate_or_deactivate_user(request, activate=True)

@admin_required
def unenroll_student(request):
    if request.method != 'POST' or 'user_id' not in request.POST or 'program' not in request.POST:
        return HttpResponseBadRequest('')
    users = ESPUser.objects.filter(id=request.POST['user_id'])
    if users.count() != 1:
        return HttpResponseBadRequest('')
    else:
        user = users[0]
        sections = user.getSections(program = request.POST['program'])
        verbs = RTC.getVisibleRegistrationTypeNames(request.POST['program'])
        for sec in sections:
            sec.unpreregister_student(user, verbs)
        return HttpResponseRedirect('/manage/userview?username=%s' % user.username)

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
    # First, if the user selected a template program, pre-populate fields with that program's data.
    template_prog = None
    template_prog_id = None
    if 'template_prog' in request.GET and (int(request.GET["template_prog"])) != 0:  # user might select `None` whose value is 0, we need to check for 0.
        template_prog_id = int(request.GET["template_prog"])
        tprogram = Program.objects.get(id=template_prog_id)
        request.session['template_prog'] = template_prog_id
        template_prog = {}
        template_prog.update(model_to_dict(tprogram))
        del template_prog["id"]
        template_prog["program_type"] = tprogram.program_type
        '''
        As Program Name should be new for each new program created then it is better to not to show old program names in input box .
        template_prog["term"] = tprogram.program_instance()
        template_prog["term_friendly"] = tprogram.niceName()
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
        line_items = pac.get_lineitemtypes(required_only=True).filter(text="Program admission").values('amount_dec')

        template_prog["base_cost"] = int(sum(x["amount_dec"] for x in line_items))
        template_prog["sibling_discount"] = tprogram.sibling_discount

    # If the form has been submitted, process it.
    if request.method == 'POST':
        form = ProgramCreationForm(request.POST)
        if form.is_valid():
            temp_prog = form.save(commit=False)
            perms, modules = prepare_program(temp_prog, form.cleaned_data)
            new_prog = form.save(commit = True)
            commit_program(new_prog, perms, form.cleaned_data['base_cost'], form.cleaned_data['sibling_discount'])
            # Create the default resource types now
            default_restypes = Tag.getTag('default_restypes')
            if default_restypes:
                resource_type_labels = json.loads(default_restypes)
                resource_types = [ResourceType.get_or_create(x, new_prog) for x in resource_type_labels]
            # If a template program was chosen, load modules based on that program's
            if template_prog is not None:
                # Force all ProgramModuleObjs and their extensions to be created now
                old_prog = Program.objects.get(id=template_prog_id)
                # If we are using another program as a template, let's copy the seq and required values from that program.
                new_prog.getModules(old_prog=old_prog)
                # Copy CRMI settings from old program
                old_crmi = ClassRegModuleInfo.objects.get(program=old_prog)
                new_crmi = ClassRegModuleInfo.objects.get(program=new_prog)
                for field in old_crmi._meta.fields:
                    if field.name not in ["id", "program"]:
                        setattr(new_crmi, field.name, getattr(old_crmi, field.name))
                new_crmi.save()
                # Copy SCRMI settings from old program
                old_scrmi = StudentClassRegModuleInfo.objects.get(program=old_prog)
                new_scrmi = StudentClassRegModuleInfo.objects.get(program=new_prog)
                for field in old_scrmi._meta.fields:
                    if field.name not in ["id", "program"]:
                        setattr(new_scrmi, field.name, getattr(old_scrmi, field.name))
                new_scrmi.save()
                # Copy tags from old program
                ct = ContentType.objects.get_for_model(old_prog)
                old_tags = Tag.objects.filter(content_type=ct, object_id=old_prog.id)
                for old_tag in old_tags:
                    # Some tags we don't want to import
                    if old_tag.key not in ['learn_extraform_id', 'teach_extraform_id', 'quiz_form_id', 'student_lottery_run']:
                        new_tag, created = Tag.objects.get_or_create(key=old_tag.key, content_type=ct, object_id=new_prog.id)
                        # Some tags get created during program creation (e.g. sibling discount), and we don't want to override those
                        if created:
                            new_tag.value = old_tag.value
                            new_tag.save()
            # If no template program is selected, create new modules
            else:
                # Create new modules
                new_prog.getModules()
            manage_url = '/manage/' + new_prog.url + '/resources'
            # While we're at it, create the program's mailing list
            if settings.USE_MAILMAN and 'mailman_moderator' in list(settings.DEFAULT_EMAIL_ADDRESSES.keys()):
                mailing_list_name = "%s_%s" % (new_prog.program_type, new_prog.program_instance)
                teachers_list_name = "%s-%s" % (mailing_list_name, "teachers")
                students_list_name = "%s-%s" % (mailing_list_name, "students")

                create_list(students_list_name, settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'])
                create_list(teachers_list_name, settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'])

                load_list_settings(teachers_list_name, "lists/program_mailman.config")
                load_list_settings(students_list_name, "lists/program_mailman.config")

                apply_list_settings(teachers_list_name, {'owner': [settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'], new_prog.director_email]})
                apply_list_settings(students_list_name, {'owner': [settings.DEFAULT_EMAIL_ADDRESSES['mailman_moderator'], new_prog.director_email]})

                if 'archive' in list(settings.DEFAULT_EMAIL_ADDRESSES.keys()):
                    add_list_members(students_list_name, [new_prog.director_email, settings.DEFAULT_EMAIL_ADDRESSES['archive']])
                    add_list_members(teachers_list_name, [new_prog.director_email, settings.DEFAULT_EMAIL_ADDRESSES['archive']])
            # Submit and create the program
            return HttpResponseRedirect(manage_url)
    # If the form has not been submitted, the default view is a blank form (or the pre-populated form with the template data).
    else:
        if template_prog:
            form = ProgramCreationForm(template_prog)
        else:
            form = ProgramCreationForm()

    return render_to_response('program/newprogram.html', request, {'form': form, 'programs': Program.objects.all().order_by('-id'), 'template_prog_id': template_prog_id})

@csrf_exempt
@transaction.non_atomic_requests
def submit_transaction(request):
    # Before we do anything else, log the raw postback to the database
    pretty_postdata = json.dumps(request.POST, sort_keys=True, indent=4,
                                 separators=(', ', ': '))
    log_record = CybersourcePostback.objects.create(post_data=pretty_postdata)
    transaction.commit()
    try:
        return _submit_transaction(request, log_record)
    except Exception:
        subject = '[ESP CC] Failed to process Cybersource postback'
        log_uri = request.build_absolute_uri(
            reverse('admin:accounting_cybersourcepostback_change', args=(log_record.id,)))
        message = 'The following Cybersource postback could not be processed. Please ' + \
                  'reconcile it by hand:\n\n    %s\n\n%s' % (log_uri, traceback.format_exc())
        from_addr = settings.SERVER_EMAIL
        recipients = [settings.DEFAULT_EMAIL_ADDRESSES['treasury']]
        send_mail(subject, message, from_addr, recipients)
        raise

@transaction.atomic
def _submit_transaction(request, log_record):
    decision = request.POST['decision']
    if decision == "ACCEPT":
        # Handle payment
        identifier = request.POST['req_merchant_defined_data1']
        amount_paid = Decimal(request.POST['req_amount'])
        transaction_id = request.POST['transaction_id']

        payment = IndividualAccountingController.record_payment_from_identifier(
            identifier, amount_paid, transaction_id)

        # Link payment to log record
        log_record.transfer = payment
        log_record.save()

        return _redirect_from_identifier(identifier, "success")
    elif decision == "DECLINE":
        identifier = request.POST['req_merchant_defined_data1']
        return _redirect_from_identifier(identifier, "declined")
    else:
        raise NotImplementedError("Can't handle decision: %s" % decision)

def _redirect_from_identifier(identifier, result):
    program = IndividualAccountingController.program_from_identifier(identifier)
    destination = "/learn/%s/cybersource?result=%s" % (program.getUrlBase(), result)
    return HttpResponseRedirect(destination)

# This really should go in qsd
@reversion.create_revision()
@admin_required
def manage_pages(request):
    if request.method == 'POST':
        data = request.POST
        if request.GET['cmd'] == 'bulk_move':
            if 'confirm' in data:
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

    elif 'cmd' in request.GET:
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
        if "reason" in request.POST and len(request.POST['reason']) > 5:
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

@cache_function
def get_email_data(start_date):
    requests = MessageRequest.objects.filter(created_at__gte=start_date).order_by('-created_at')

    requests_list = []
    for req in requests:
        toes = TextOfEmail.objects.filter(created_at=req.created_at,
                                          subject = req.subject,
                                          send_from = req.sender)
        if req.processed:
            req.num_rec = toes.count()
        else:
            req.num_rec = CommModule.approx_num_of_recipients(req.recipients, req.get_sendto_fn())
        req.num_sent = toes.filter(sent__isnull=False).count()
        if req.num_rec == req.num_sent:
            last_email = toes.order_by('-sent').first()
            if last_email is not None:
                req.finished_at = last_email.sent
            else:
                req.finished_at = "(Not finished)"
        else:
            req.finished_at = "(Not finished)"
        requests_list.append(req)
    return requests_list
get_email_data.depend_on_model(MessageRequest)
get_email_data.depend_on_model(TextOfEmail)

@admin_required
def emails(request):
    """
    View that displays information for recent email requests.
    GET data:
      'start_date' (optional):  Starting date to filter email requests by.
                                Should be given in the format "%m/%d/%Y".
    """
    context = {}
    if request.GET and "start_date" in request.GET:
        start_date = datetime.datetime.strptime(request.GET["start_date"], "%Y-%m-%d")
    else:
        start_date = datetime.date.today() - datetime.timedelta(30)
    context['start_date'] = start_date

    context['requests'] = get_email_data(start_date)

    return render_to_response('admin/emails.html', request, context)

@admin_required
def tags(request, section=""):
    context = {}

    #If one of the forms was submitted, process it and save if valid
    if request.method == 'POST':
        form = TagSettingsForm(request.POST)
        if form.is_valid():
            form.save()
            form = TagSettingsForm() # replace null responses with defaults if processed successfully
    else:
        form = TagSettingsForm()

    context['form'] = form
    context['categories'] = form.categories
    context['open_section'] = section

    return render_to_response('program/modules/admincore/tags.html', request, context)

@admin_required
def redirects(request, section=""):
    """
    View that lets admins create/edit URL and email redirects
    """
    context = {}
    redirect_form = RedirectForm()
    email_redirect_form = PlainRedirectForm()

    if request.method == 'POST':
        if request.POST.get('object') == 'redirect':
            section = 'redirects'
            if request.POST.get('command') == 'add': # New redirect
                redirect_form = RedirectForm(request.POST)
                if redirect_form.is_valid():
                    redirect = redirect_form.save(commit=False)
                    redirect.site = Site.objects.get_current()
                    redirect.save()
                    redirect_form = RedirectForm()
            elif request.POST.get('command') == 'load': # Load existing redirect into form
                redirect_id = request.POST.get('id')
                redirects = Redirect.objects.filter(id = redirect_id)
                if redirects.count() == 1:
                    redirect = redirects[0]
                    redirect_form = RedirectForm(instance = redirect)
            elif request.POST.get('command') == 'edit': # Edit existing redirect
                redirect_id = request.POST.get('id')
                redirects = Redirect.objects.filter(id = redirect_id)
                if redirects.count() == 1:
                    redirect = redirects[0]
                    redirect_form = RedirectForm(request.POST, instance = redirect)
                    if redirect_form.is_valid():
                        redirect_form.save()
                        redirect_form = RedirectForm()
            elif request.POST.get('command') == 'delete': # Delete redirect
                redirect_id = request.POST.get('id')
                redirects = Redirect.objects.filter(id = redirect_id)
                if redirects.count() == 1:
                    redirect = redirects[0]
                    redirect.delete()
        elif request.POST.get('object') == 'email_redirect':
            section = 'email_redirects'
            if request.POST.get('command') == 'add': # New email redirect
                email_redirect_form = PlainRedirectForm(request.POST)
                if email_redirect_form.is_valid():
                    email_redirect_form.save()
                    email_redirect_form = PlainRedirectForm()
            elif request.POST.get('command') == 'load': # Load existing email redirect into form
                redirect_id = request.POST.get('id')
                redirects = PlainRedirect.objects.filter(id = redirect_id)
                if redirects.count() == 1:
                    redirect = redirects[0]
                    email_redirect_form = PlainRedirectForm(instance = redirect)
            elif request.POST.get('command') == 'edit': # Edit existing email redirect
                redirect_id = request.POST.get('id')
                redirects = PlainRedirect.objects.filter(id = redirect_id)
                if redirects.count() == 1:
                    redirect = redirects[0]
                    email_redirect_form = PlainRedirectForm(request.POST, instance = redirect)
                    if email_redirect_form.is_valid():
                        email_redirect_form.save()
                        email_redirect_form = PlainRedirectForm()
            elif request.POST.get('command') == 'delete': # Delete email redirect
                redirect_id = request.POST.get('id')
                redirects = PlainRedirect.objects.filter(id = redirect_id)
                if redirects.count() == 1:
                    redirect = redirects[0]
                    redirect.delete()
    context['open_section'] = section
    context['redirect_form'] = redirect_form
    context['email_redirect_form'] = email_redirect_form
    context['redirects'] = Redirect.objects.all()
    context['email_redirects'] = PlainRedirect.objects.all()

    return render_to_response('program/redirects.html', request, context)

@admin_required
def catsflagsrecs(request, section=""):
    """
    View that lets admins create/edit class categories and flag types
    """
    context = {}
    cat_form = CategoryForm(initial={'symbol': ''})
    flag_form = FlagTypeForm()
    rec_form = RecordTypeForm()

    if request.method == 'POST':
        if request.POST.get('object') == 'category':
            section = 'categories'
            if request.POST.get('command') == 'add': # New category
                cat_form = CategoryForm(request.POST)
                if cat_form.is_valid():
                    cat_form.save()
                    cat_form = CategoryForm()
            elif request.POST.get('command') == 'load': # Load existing category into form
                cat_id = request.POST.get('id')
                cats = ClassCategories.objects.filter(id = cat_id)
                if cats.count() == 1:
                    cat = cats[0]
                    cat_form = CategoryForm(instance = cat)
            elif request.POST.get('command') == 'edit': # Edit existing category
                cat_id = request.POST.get('id')
                cats = ClassCategories.objects.filter(id = cat_id)
                if cats.count() == 1:
                    cat = cats[0]
                    cat_form = CategoryForm(request.POST, instance = cat)
                    if cat_form.is_valid():
                        cat_form.save()
                        cat_form = CategoryForm()
            elif request.POST.get('command') == 'delete': # Delete category
                cat_id = request.POST.get('id')
                cats = ClassCategories.objects.filter(id = cat_id)
                if cats.count() == 1:
                    cat = cats[0]
                    cat.delete()
        elif request.POST.get('object') == 'flag_type':
            section = 'flagtypes'
            if request.POST.get('command') == 'add': # New flag type
                flag_form = FlagTypeForm(request.POST)
                if flag_form.is_valid():
                    flag_form.save()
                    flag_form = FlagTypeForm()
            elif request.POST.get('command') == 'load': # Load existing flag type into form
                ft_id = request.POST.get('id')
                fts = ClassFlagType.objects.filter(id = ft_id)
                if fts.count() == 1:
                    ft = fts[0]
                    flag_form = FlagTypeForm(instance = ft)
            elif request.POST.get('command') == 'edit': # Edit existing flag type
                ft_id = request.POST.get('id')
                fts = ClassFlagType.objects.filter(id = ft_id)
                if fts.count() == 1:
                    ft = fts[0]
                    flag_form = FlagTypeForm(request.POST, instance = ft)
                    if flag_form.is_valid():
                        flag_form.save()
                        flag_form = FlagTypeForm()
            elif request.POST.get('command') == 'delete': # Delete flag type
                ft_id = request.POST.get('id')
                fts = ClassFlagType.objects.filter(id = ft_id)
                if fts.count() == 1:
                    ft = fts[0]
                    ft.delete()
        elif request.POST.get('object') == 'record_type':
            section = 'recordtypes'
            if request.POST.get('command') == 'add': # New record type
                rec_form = RecordTypeForm(request.POST)
                if rec_form.is_valid():
                    rec_form.save()
                    rec_form = RecordTypeForm()
            elif request.POST.get('command') == 'load': # Load existing record type into form
                ft_id = request.POST.get('id')
                fts = RecordType.objects.filter(id = ft_id)
                if fts.count() == 1:
                    ft = fts[0]
                    rec_form = RecordTypeForm(instance = ft)
            elif request.POST.get('command') == 'edit': # Edit existing record type
                rt_id = request.POST.get('id')
                rts = RecordType.objects.filter(id = rt_id)
                if rts.count() == 1:
                    rt = rts[0]
                    rec_form = RecordTypeForm(request.POST, instance = rt)
                    if rec_form.is_valid():
                        rec_form.save()
                        rec_form = RecordTypeForm()
            elif request.POST.get('command') == 'delete': # Delete record type
                rt_id = request.POST.get('id')
                rts = RecordType.objects.filter(id = rt_id)
                if rts.count() == 1:
                    rt = rts[0]
                    rt.delete()
    context['open_section'] = section
    context['cat_form'] = cat_form
    context['flag_form'] = flag_form
    context['rec_form'] = rec_form
    context['categories'] = ClassCategories.objects.all().order_by('seq')
    context['flag_types'] = ClassFlagType.objects.all().order_by('seq')
    rec_types = RecordType.objects.all().order_by('id')
    context['record_types'] = sorted(rec_types, key = lambda x:x.is_custom(), reverse=True)

    return render_to_response('program/categories_and_flags.html', request, context)

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
            return HttpResponse(json.dumps(result), content_type='application/json')

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

            #   Get list of users the query applies to
            users_q = Q()
            for program in programs:
                if 'student_reg_types' in form.cleaned_data and form.cleaned_data['student_reg_types']:
                    students_objects = program.students(QObjects=True)
                    for reg_type in form.cleaned_data['student_reg_types']:
                        if reg_type in list(students_objects.keys()):
                            users_q = users_q | students_objects[reg_type]
                elif 'teacher_reg_types' in form.cleaned_data and form.cleaned_data['teacher_reg_types']:
                    teachers_objects = program.teachers(QObjects=True)
                    for reg_type in form.cleaned_data['teacher_reg_types']:
                        if reg_type in list(teachers_objects.keys()):
                            users_q = users_q | teachers_objects[reg_type]

            #   Narrow down by school (perhaps not ideal results, but faster)
            if form.cleaned_data['school_query_type'] == 'name':
                users_q = users_q & (Q(studentinfo__school__icontains=form.cleaned_data['school_name']) | Q(studentinfo__k12school__name__icontains=form.cleaned_data['school_name']))
            elif form.cleaned_data['school_query_type'] == 'list':
                k12school_ids = []
                school_names = []
                for item in form.cleaned_data['school_multisel']:
                    if item.startswith('K12:'):
                        k12school_ids.append(int(item[4:]))
                    elif item.startswith('Sch:'):
                        school_names.append(item[4:])
                users_q = users_q & (Q(studentinfo__school__in=school_names) | Q(studentinfo__k12school__id__in=k12school_ids))

            #   Narrow down by Zip code, simply using the latest profile
            #   Note: it would be harder to track users better (i.e. zip code A in fall 2008, zip code B in fall 2009)
            if form.cleaned_data['zip_query_type'] == 'exact':
                users_q = users_q & Q(registrationprofile__contact_user__address_zip=form.cleaned_data['zip_code'], registrationprofile__most_recent_profile=True)
            elif form.cleaned_data['zip_query_type'] == 'partial':
                users_q = users_q & Q(registrationprofile__contact_user__address_zip__startswith=form.cleaned_data['zip_code_partial'], registrationprofile__most_recent_profile=True)
            elif form.cleaned_data['zip_query_type'] == 'distance':
                zipc = ZipCode.objects.get(zip_code=form.cleaned_data['zip_code'])
                zipcodes = zipc.close_zipcodes(form.cleaned_data['zip_code_distance'])
                users_q = users_q & Q(registrationprofile__contact_user__address_zip__in = zipcodes, registrationprofile__most_recent_profile=True)

            users = ESPUser.objects.filter(users_q).distinct()
            result_dict['num_users'] = users.count()
            user_list = list(users)
            # Batch-fetch latest profile per user to avoid N+1
            profile_by_user = {}
            if user_list:
                for p in RegistrationProfile.objects.filter(user__in=users).select_related('user').order_by('user_id', '-last_ts'):
                    if p.user_id not in profile_by_user:
                        profile_by_user[p.user_id] = p
            profiles = [profile_by_user.get(u.id) or RegistrationProfile(user=u) for u in user_list]

            #   Accumulate desired information for selected query
            from esp.program import statistics as statistics_functions
            if hasattr(statistics_functions, form.cleaned_data['query']):
                context['result'] = getattr(statistics_functions, form.cleaned_data['query'])(form, programs, users, profiles, result_dict)
            else:
                context['result'] = 'Unsupported query'

            #   Generate response
            form.hide_unwanted_fields()
            context['form'] = form
            context['clear_first'] = False
            context['field_ids'] = get_field_ids(form)

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                result = {}
                result['result_html'] = context['result']
                result['script'] = render_to_string('program/statistics/script.js', context)
                return HttpResponse(json.dumps(result), content_type='application/json')
            else:
                return render_to_response('program/statistics.html', request, context)
        else:
            #   Form was submitted but there are problems with it
            form.hide_unwanted_fields()
            context = {'form': form}
            context['clear_first'] = False
            context['field_ids'] = get_field_ids(form)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return HttpResponse(json.dumps(result), content_type='application/json')
            else:
                return render_to_response('program/statistics.html', request, context)

    #   First request, form not yet submitted
    form = StatisticsQueryForm(program=program)
    form.hide_unwanted_fields()
    context = {'form': form}
    context['clear_first'] = False
    context['field_ids'] = get_field_ids(form)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponse(json.dumps(context), content_type='application/json')
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


@admin_required
def manage_docs(request, doc_path=None):
    """Render admin documentation pages embedded within the website."""
    from django.http import Http404, FileResponse, HttpResponseRedirect

    doc_html = None
    doc_title = 'Admin Documentation'

    if doc_path:
        # Strip trailing slash so /releases/16/ is treated as /releases/16
        doc_path = doc_path.rstrip('/')
        if not doc_path:
            raise Http404
        # Redirect index.html to the docs root
        if doc_path == 'index.html':
            return HttpResponseRedirect('/manage/docs/')
        # Security: validate path only contains safe characters (whitelist)
        # before joining with DOCS_ADMIN_ROOT to prevent path traversal.
        if not re.match(r'^[A-Za-z0-9_./-]+$', doc_path) or '..' in doc_path:
            raise Http404
        # Resolve the full path and confirm it stays inside DOCS_ADMIN_ROOT
        requested = os.path.realpath(os.path.join(DOCS_ADMIN_ROOT, doc_path))
        if not requested.startswith(DOCS_ADMIN_ROOT + os.sep):
            raise Http404
        if os.path.isdir(requested):
            requested = os.path.join(requested, 'README.rst')
        if not os.path.isfile(requested):
            raise Http404

        # If the requested file is not RST (e.g., an image), serve it directly
        if not requested.endswith('.rst'):
            content_type, _ = mimetypes.guess_type(requested)
            if not content_type:
                content_type = 'application/octet-stream'
            try:
                return FileResponse(open(requested, 'rb'), content_type=content_type)
            except OSError:
                raise Http404

        # Parse RST normally
        try:
            with open(requested, 'r', encoding='utf-8') as f:
                rst_text = f.read()
        except OSError:
            raise Http404
        doc_html = _rst_to_html(rst_text)

        # Consistent title extraction using our helper
        doc_title = _extract_rst_title(requested) or 'Admin Documentation'

    latest_release_label, latest_release_html = _latest_release()

    context = {
        'doc_nav': _docs_nav(),
        'doc_html': doc_html,
        'doc_title': doc_title,
        'doc_path': doc_path,
        'latest_release_label': latest_release_label,
        'latest_release_html': latest_release_html,
    }
    return render_to_response('program/manage_docs.html', request, context)
