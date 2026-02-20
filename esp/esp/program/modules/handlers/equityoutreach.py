from __future__ import absolute_import

from django.db.models import Q

from esp.program.models import FinancialAidRequest, RegistrationProfile, StudentRegistration
from esp.users.models import ESPUser


class EquityOutreachCohorts(object):
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
        "bus",
        "train",
        "public",
        "ride",
        "carpool",
        "cannot",
        "can't",
        "difficult",
        "hard",
        "other",
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

    @classmethod
    def cohort_summaries(cls, program):
        summaries = []
        for key in cls.all_cohort_keys():
            qs = cls.users_for_cohort(program, key)
            summaries.append(
                {
                    "key": key,
                    "label": cls.cohort_label(key),
                    "count": qs.count(),
                }
            )
        return summaries

