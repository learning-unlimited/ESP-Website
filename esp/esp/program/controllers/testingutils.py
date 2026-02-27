
from __future__ import absolute_import

__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2025 by the individual contributors
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

from django.db import transaction

from esp.program.models import (
    StudentRegistration, StudentSubjectInterest, PhaseZeroRecord,
    ModeratorRecord, VolunteerOffer, RegistrationProfile, FinancialAidRequest,
)
from esp.program.models.app_ import StudentApplication
from esp.program.models.class_ import ClassSubject
from esp.users.models import Record, UserAvailability

logger = logging.getLogger(__name__)


class TestDataCleanupController(object):
    """Centralises the logic for wiping test registration data for a single
    user within a program.  This is intentionally kept separate from the view
    layer so it can be tested independently and reused if needed.

    Usage::

        ctrl = TestDataCleanupController(program, user)
        counts = ctrl.get_counts()   # preview — no side effects
        ctrl.execute()               # permanent deletion
    """

    def __init__(self, program, user):
        self.program = program
        self.user = user

    # ------------------------------------------------------------------
    # Querysets — each scoped strictly to (program, user)
    # ------------------------------------------------------------------

    def _sr_qs(self):
        return StudentRegistration.objects.filter(
            section__parent_class__parent_program=self.program, user=self.user)

    def _ssi_qs(self):
        return StudentSubjectInterest.objects.filter(
            subject__parent_program=self.program, user=self.user)

    def _pzr_qs(self):
        return PhaseZeroRecord.objects.filter(program=self.program, user=self.user)

    def _fin_aid_qs(self):
        return FinancialAidRequest.objects.filter(program=self.program, user=self.user)

    def _app_qs(self):
        return StudentApplication.objects.filter(program=self.program, user=self.user)

    def _taught_classes(self):
        """All ClassSubject records for this program where user is a teacher."""
        return ClassSubject.objects.filter(
            parent_program=self.program, teachers=self.user)

    def _sole_teacher_class_ids(self):
        """IDs of classes where the user is the *only* teacher."""
        return [
            cls.id for cls in self._taught_classes()
            if cls.teachers.count() == 1
        ]

    def _moderator_qs(self):
        return ModeratorRecord.objects.filter(program=self.program, user=self.user)

    def _ua_qs(self):
        return UserAvailability.objects.filter(
            event__program=self.program, user=self.user)

    def _vol_qs(self):
        return VolunteerOffer.objects.filter(
            request__program=self.program, user=self.user)

    def _reg_profile_qs(self):
        return RegistrationProfile.objects.filter(
            program=self.program, user=self.user)

    def _rec_qs(self):
        return Record.objects.filter(program=self.program, user=self.user)

    def _custom_form_counts_and_models(self):
        """Return a list of (count, dyn_model) for CustomForm response tables
        linked to this program, or an empty list if unavailable.

        CustomForms uses dynamically generated tables and a circular import
        prevents top-level importing of these modules.
        """
        result = []
        try:
            from esp.customforms.DynamicModel import DynamicModelHandler  # noqa: E402
            from esp.customforms.models import Form as CustomForm         # noqa: E402
            for form in CustomForm.objects.filter(link_type='Program', link_id=self.program.id):
                try:
                    dyn_model = DynamicModelHandler(form).createDynModel()
                    if dyn_model is not None and not form.anonymous:
                        result.append((dyn_model.objects.filter(user=self.user).count(), dyn_model))
                except Exception:
                    pass
        except Exception:
            pass
        return result

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_counts(self):
        """Return a dict of {label: int} showing how many objects each
        category would delete.  Has no side effects.
        """
        sole_ids = self._sole_teacher_class_ids()
        taught = self._taught_classes()
        custom_count = sum(c for c, _ in self._custom_form_counts_and_models())

        return {
            'student_registrations': self._sr_qs().count(),
            'subject_interests': self._ssi_qs().count(),
            'phase_zero_records': self._pzr_qs().count(),
            'financial_aid_requests': self._fin_aid_qs().count(),
            'student_applications': self._app_qs().count(),
            'taught_classes_deleted': len(sole_ids),
            'taught_classes_removed': taught.count() - len(sole_ids),
            'moderator_records': self._moderator_qs().count(),
            'availabilities': self._ua_qs().count(),
            'volunteer_offers': self._vol_qs().count(),
            'registration_profiles': self._reg_profile_qs().count(),
            'records': self._rec_qs().count(),
            'custom_form_responses': custom_count,
        }

    def execute(self):
        """Permanently delete all test data for (program, user) inside a
        single atomic transaction.  Raises on failure; the caller is
        responsible for logging the action.
        """
        sole_ids = self._sole_teacher_class_ids()

        with transaction.atomic():
            # Student-side
            self._sr_qs().delete()
            self._ssi_qs().delete()
            self._fin_aid_qs().delete()
            self._app_qs().delete()  # cascades StudentAppResponse via M2M

            # Teacher-side
            # Delete classes where user is the sole teacher; ClassSection
            # objects are removed via the default on_delete=CASCADE.
            ClassSubject.objects.filter(id__in=sole_ids).delete()
            # For co-taught classes, only remove the user from the M2M.
            for cls in self._taught_classes():
                cls.teachers.remove(self.user)
            self._moderator_qs().delete()

            # Shared
            self._ua_qs().delete()
            self._vol_qs().delete()
            self._reg_profile_qs().delete()

            # PhaseZeroRecord.user is M2M; remove the user, then clean up
            # any records that are now empty.
            for pzr in list(self._pzr_qs()):
                pzr.user.remove(self.user)
                if pzr.user.count() == 0:
                    pzr.delete()

            self._rec_qs().delete()

            # CustomForm responses (dynamically generated tables)
            for _, dyn_model in self._custom_form_counts_and_models():
                try:
                    dyn_model.objects.filter(user=self.user).delete()
                except Exception:
                    pass
