import re
import operator
import datetime
import json
from functools import reduce
from django.db.models import Q, Min
from django.http import HttpResponseRedirect, HttpResponseBadRequest, HttpResponse
from django.conf import settings
from esp.utils.web import render_to_response
from esp.program.models import Program, TeacherBio, RegistrationProfile, StudentSubjectInterest, VolunteerOffer, UserAvailability
from esp.users.models import ESPUser, admin_required, GradeChangeRequest
from esp.middleware import ESPError
from esp.program.modules.handlers.studentregcore import StudentRegCore
from django.contrib.auth.decorators import login_required

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
    re.match(r"\A\(\d\d\d\)\Z", userstr_parts[0]) and \
    re.match(r"[^A-Za-z]*", userstr_parts[1]):
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

@admin_required
def userview_edit(request):
    """ Handle AJAX updates for user information from userview """
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError

    if request.method != 'POST':
        return HttpResponseBadRequest('Only POST requests are allowed.')

    try:
        user = ESPUser.objects.get(username=request.POST.get('username'))
    except ESPUser.DoesNotExist:
        return HttpResponseBadRequest('User not found.')

    field = request.POST.get('field')

    if field == 'name':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        if not first_name and not last_name:
            return HttpResponseBadRequest('At least one of first or last name must be provided.')
        user.first_name = first_name
        user.last_name = last_name
    elif field == 'email':
        email = request.POST.get('email', '').strip()
        if email:
            try:
                validate_email(email)
            except ValidationError:
                return HttpResponseBadRequest('Invalid email address.')
        user.email = email
    else:
        return HttpResponseBadRequest('Invalid field.')

    user.save()
    return HttpResponse(json.dumps({'success': True}), content_type="application/json")

def deactivate_user(request):
    return activate_or_deactivate_user(request, activate=False)

def activate_user(request):
    return activate_or_deactivate_user(request, activate=True)

@admin_required
def unenroll_student(request):
    from esp.program.controllers.studentclassregmodule import RegistrationTypeController as RTC
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
