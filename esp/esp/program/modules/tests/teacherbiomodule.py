__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2026 by the individual contributors
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

from esp.program.tests import ProgramFrameworkTest


class TeacherBioModuleTest(ProgramFrameworkTest):
    """
    Tests for TeacherBioModule.isCompleted().

    Issue #2467: when TeacherBioModule is required, the registration flow
    would not advance to the next page even after the teacher submitted their
    biography.  The root cause was that the old isCompleted() required BOTH
    `bio` AND `slugbio` to be truthy; since `slugbio` is an optional form
    field, leaving it blank produced a valid saved record (id is not None,
    bio is non-empty) that was still treated as incomplete.

    The fix drops `slugbio` from the completion check: only a saved record
    with a non-empty `bio` is required.
    """

    def setUp(self, *args, **kwargs):
        from esp.program.modules.base import ProgramModule, ProgramModuleObj

        kwargs.update({'num_teachers': 2})
        super().setUp(*args, **kwargs)

        m = ProgramModule.objects.get(handler='TeacherBioModule', module_type='teach')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, m)

    # ------------------------------------------------------------------
    # Helper: set the active user on the module.
    # isCompleted() checks hasattr(self, 'user') first, so setting
    # self.moduleobj.user is sufficient; get_current_request() is never reached.
    # ------------------------------------------------------------------
    def _set_user(self, user):
        self.moduleobj.user = user

    # ------------------------------------------------------------------
    # Test 1: no bio record at all → incomplete
    # ------------------------------------------------------------------
    def test_no_bio_is_incomplete(self):
        from esp.program.models import TeacherBio
        teacher = self.teachers[0]
        self._set_user(teacher)

        # Make sure there is no bio for this teacher/program
        TeacherBio.objects.filter(user=teacher, program=self.program).delete()

        self.assertFalse(
            self.moduleobj.isCompleted(),
            "isCompleted() must be False when no TeacherBio record exists."
        )

    # ------------------------------------------------------------------
    # Test 2: saved bio with non-empty `bio` but empty `slugbio` → COMPLETE
    # This is the exact scenario from issue #2467.
    # ------------------------------------------------------------------
    def test_bio_without_slugbio_is_complete(self):
        from esp.program.models import TeacherBio
        teacher = self.teachers[0]
        self._set_user(teacher)

        TeacherBio.objects.filter(user=teacher, program=self.program).delete()
        bio = TeacherBio(user=teacher, program=self.program,
                         bio="I love teaching physics.", slugbio="")
        bio.save()

        self.assertTrue(
            self.moduleobj.isCompleted(),
            "isCompleted() must be True when bio text is present even if slugbio is empty "
            "(regression for issue #2467)."
        )

    # ------------------------------------------------------------------
    # Test 3: saved bio with both `bio` and `slugbio` → still complete
    # ------------------------------------------------------------------
    def test_bio_with_slugbio_is_complete(self):
        from esp.program.models import TeacherBio
        teacher = self.teachers[1]
        self._set_user(teacher)

        TeacherBio.objects.filter(user=teacher, program=self.program).delete()
        bio = TeacherBio(user=teacher, program=self.program,
                         bio="I love teaching chemistry.", slugbio="Chem teacher")
        bio.save()

        self.assertTrue(
            self.moduleobj.isCompleted(),
            "isCompleted() must be True when both bio and slugbio are non-empty."
        )

    # ------------------------------------------------------------------
    # Test 4: saved record in DB but bio text is empty → incomplete
    # (a teacher can theoretically save an empty form; that must not count)
    # ------------------------------------------------------------------
    def test_empty_bio_text_is_incomplete(self):
        from esp.program.models import TeacherBio
        teacher = self.teachers[0]
        self._set_user(teacher)

        TeacherBio.objects.filter(user=teacher, program=self.program).delete()
        bio = TeacherBio(user=teacher, program=self.program,
                         bio="", slugbio="Some tagline")
        bio.save()

        self.assertFalse(
            self.moduleobj.isCompleted(),
            "isCompleted() must be False when bio text is empty, even if the record has an id."
        )
