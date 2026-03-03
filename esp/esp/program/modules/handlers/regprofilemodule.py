
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
from esp.program.modules.base import ProgramModuleObj, usercheck_usetl, main_call, meets_deadline
from esp.program.models import FinancialAidRequest, RegistrationProfile, StudentRegistration
from esp.users.models   import ESPUser
from django.db.models.query import Q
from esp.middleware.threadlocalrequest import get_current_request


class _EquityOutreachCohorts(object):
    """At-risk student cohorts exposed as user lists (equity_*) in students()/studentDesc()."""

    COHORT_INCOMPLETE_REGISTRATION = "incomplete_registration"
    COHORT_UNCONFIRMED_REGISTRATION = "unconfirmed_registration"
    COHORT_INCOMPLETE_FINAID = "incomplete_financial_aid"
    COHORT_TRANSPORTATION_BARRIER = "transportation_barrier"
    COHORT_LOW_HOURS_OR_WAITLISTED = "low_hours_or_waitlisted"

    COHORT_LABELS = {
        COHORT_INCOMPLETE_REGISTRATION: "Started profile but not confirmed",
        COHORT_UNCONFIRMED_REGISTRATION: "Enrolled in classes but not confirmed",
        COHORT_INCOMPLETE_FINAID: "Financial aid started but incomplete",
        COHORT_TRANSPORTATION_BARRIER: "Potential transportation barrier",
        COHORT_LOW_HOURS_OR_WAITLISTED: "Low class-hours or waitlisted",
    }

    TRANSPORTATION_SIGNAL_KEYWORDS = (
        "bus", "train", "public", "ride", "carpool",
        "cannot", "can't", "difficult", "hard", "other",
    )

    @classmethod
    def all_cohort_keys(cls):
        return [
            cls.COHORT_INCOMPLETE_REGISTRATION,
            cls.COHORT_UNCONFIRMED_REGISTRATION,
            cls.COHORT_INCOMPLETE_FINAID,
            cls.COHORT_TRANSPORTATION_BARRIER,
            cls.COHORT_LOW_HOURS_OR_WAITLISTED,
        ]

    @classmethod
    def cohort_label(cls, cohort_key):
        return cls.COHORT_LABELS.get(cohort_key, cohort_key.replace("_", " ").title())

    @classmethod
    def users_for_cohort(cls, program, cohort_key):
        dispatch = {
            cls.COHORT_INCOMPLETE_REGISTRATION: cls._incomplete_registration_users,
            cls.COHORT_UNCONFIRMED_REGISTRATION: cls._unconfirmed_registration_users,
            cls.COHORT_INCOMPLETE_FINAID: cls._incomplete_finaid_users,
            cls.COHORT_TRANSPORTATION_BARRIER: cls._transportation_barrier_users,
            cls.COHORT_LOW_HOURS_OR_WAITLISTED: cls._low_hours_or_waitlisted_users,
        }
        if cohort_key not in dispatch:
            return ESPUser.objects.none()
        return dispatch[cohort_key](program)

    @classmethod
    def _confirmed_ids(cls, program):
        return ESPUser.objects.filter(
            record__event__name="reg_confirmed",
            record__program=program,
        ).values_list("id", flat=True)

    @classmethod
    def _enrolled_student_ids(cls, program):
        return StudentRegistration.valid_objects().filter(
            section__parent_class__parent_program=program,
            relationship__name="Enrolled",
        ).values_list("user_id", flat=True).distinct()

    @classmethod
    def _waitlisted_student_ids(cls, program):
        return StudentRegistration.valid_objects().filter(
            section__parent_class__parent_program=program,
            relationship__name__startswith="Waitlist",
        ).values_list("user_id", flat=True).distinct()

    @classmethod
    def _program_students_with_profiles(cls, program):
        return ESPUser.objects.filter(
            registrationprofile__program=program,
            registrationprofile__student_info__isnull=False,
            registrationprofile__most_recent_profile=True,
        ).distinct()

    @classmethod
    def _incomplete_registration_users(cls, program):
        return cls._program_students_with_profiles(program).exclude(id__in=cls._confirmed_ids(program))

    @classmethod
    def _unconfirmed_registration_users(cls, program):
        return ESPUser.objects.filter(id__in=cls._enrolled_student_ids(program)).exclude(
            id__in=cls._confirmed_ids(program)
        ).distinct()

    @classmethod
    def _incomplete_finaid_users(cls, program):
        pending_users = FinancialAidRequest.objects.filter(program=program, done=False).values_list("user_id", flat=True)
        return ESPUser.objects.filter(id__in=pending_users).distinct()

    @classmethod
    def _transportation_barrier_users(cls, program):
        signal_q = Q()
        for keyword in cls.TRANSPORTATION_SIGNAL_KEYWORDS:
            signal_q |= Q(registrationprofile__student_info__transportation__icontains=keyword)
        return ESPUser.objects.filter(
            registrationprofile__program=program,
            registrationprofile__student_info__isnull=False,
            registrationprofile__most_recent_profile=True,
        ).filter(signal_q).exclude(
            registrationprofile__student_info__transportation=""
        ).distinct()

    @classmethod
    def _low_hours_or_waitlisted_users(cls, program):
        waitlisted_ids = set(cls._waitlisted_student_ids(program))
        low_hour_ids = set()
        for user in ESPUser.objects.filter(id__in=cls._enrolled_student_ids(program)).distinct():
            class_hours = sum(section.meeting_times.count() for section in user.getEnrolledSections(program))
            if class_hours <= 1:
                low_hour_ids.add(user.id)
        return ESPUser.objects.filter(id__in=(waitlisted_ids | low_hour_ids)).distinct()


# Public alias for tests and any external use
EquityOutreachCohorts = _EquityOutreachCohorts


# reg profile module
class RegProfileModule(ProgramModuleObj):
    doc = """Serves the profile editor during student and/or teacher registration."""

    @classmethod
    def module_properties(cls):
        return [ {
            "admin_title": "Student Profile Editor",
            "link_title": "Update Your Profile",
            "module_type": "learn",
            "seq": 0,
            "required": True,
            "choosable": 1
        }, {
            "admin_title": "Teacher Profile Editor",
            "link_title": "Update Your Profile",
            "module_type": "teach",
            "seq": 0,
            "required": True,
            "choosable": 1,
        } ]

    def students(self, QObject = False):
        if QObject:
            result = {'student_profile': Q(registrationprofile__program = self.program, registrationprofile__student_info__isnull = False)}
        else:
            students = ESPUser.objects.filter(registrationprofile__program = self.program, registrationprofile__student_info__isnull = False).distinct()
            result = {'student_profile': students}
        for key in _EquityOutreachCohorts.all_cohort_keys():
            qs = _EquityOutreachCohorts.users_for_cohort(self.program, key)
            list_name = "equity_" + key
            if QObject:
                result[list_name] = Q(id__in=qs.values_list("id", flat=True))
            else:
                result[list_name] = qs.distinct()
        return result

    def studentDesc(self):
        result = {'student_profile': """Students who have filled out a profile"""}
        for key in _EquityOutreachCohorts.all_cohort_keys():
            result["equity_" + key] = _EquityOutreachCohorts.cohort_label(key)
        return result

    def teachers(self, QObject = False):
        if QObject:
            return {'teacher_profile': Q(registrationprofile__program=self.program) &
                                       Q(registrationprofile__teacher_info__isnull=False)}
        teachers = ESPUser.objects.filter(registrationprofile__program = self.program, registrationprofile__teacher_info__isnull = False).distinct()
        return {'teacher_profile': teachers }

    def teacherDesc(self):
        return {'teacher_profile': """Teachers who have filled out a profile"""}

    @main_call
    @usercheck_usetl
    @meets_deadline("/Profile")
    def profile(self, request, tl, one, two, module, extra, prog):
        """ Display the registration profile page, the page that contains the contact information for a student, as attached to a particular program """

        from esp.web.views.myesp import profile_editor

        #   Check user role.  Some users may have multiple roles; if one of them
        #   is 'student' or 'teacher' then use that to set up the profile.
        #   Otherwise, make a wild guess.
        user_roles = request.user.getUserTypes()
        user_roles = [x.lower() for x in user_roles]
        if 'teacher' in user_roles or 'student' in user_roles:
            role = {'teach': 'teacher','learn': 'student'}[tl]
        else:
            role = user_roles[0]

        #   Reset email address for program registrations.
        if prog is None:
            regProf = RegistrationProfile.getLastProfile(request.user)
        else:
            regProf = RegistrationProfile.getLastForProgram(request.user, prog)

        # aseering 8/20/2007: It is possible for a user to not have a
        # contact_user associated with their registration profile.
        # Deal nicely with this.
        if hasattr(regProf.contact_user, 'e_mail'):
            regProf.contact_user.e_mail = ''
            regProf.contact_user.save()

        response = profile_editor(request, prog, False, role)
        if response == True:
            return self.goToCore(tl)
        return response

    def isCompleted(self):
        if hasattr(self, 'user'):
            user = self.user
        else:
            user = get_current_request().user
        regProf = RegistrationProfile.getLastForProgram(user, self.program, self.module.module_type)
        return regProf.id is not None

    class Meta:
        proxy = True
        app_label = 'modules'
