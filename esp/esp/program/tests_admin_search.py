from django.test import RequestFactory

from esp.admin import admin_site
from esp.program.admin import StudentRegistrationAdmin, StudentSubjectInterestAdmin
from esp.program.models import (RegistrationType, StudentRegistration,
                                StudentSubjectInterest)
from esp.program.tests import ProgramFrameworkTest


class AdminSearchTest(ProgramFrameworkTest):
    """Tests for the student registration / interest admin search.

    These admins search over some of the largest tables on the site, so their
    `search_fields` use the cheaper `^` (starts with) and `=` (exact) lookups
    for user names and IDs.  These tests pin down that those lookups still find
    the things admins expect to be able to search for.
    """

    def setUp(self):
        super().setUp(num_students=1, num_teachers=1, classes_per_teacher=1,
                      sections_per_class=1, num_timeslots=1)
        self.student = self.students[0]
        self.student.first_name = 'Hermione'
        self.student.last_name = 'Granger'
        self.student.email = 'hjg@example.com'
        self.student.save()

        self.subject = self.program.classes()[0]
        self.subject.title = 'Advanced Potion-Making'
        self.subject.save()
        self.section = self.subject.get_sections()[0]

        self.registration = StudentRegistration.objects.create(
            user=self.student, section=self.section,
            relationship=RegistrationType.objects.get_or_create(name='Enrolled')[0],
        )
        self.interest = StudentSubjectInterest.objects.create(
            user=self.student, subject=self.subject,
        )

        self.request = RequestFactory().get('/')
        self.reg_admin = StudentRegistrationAdmin(StudentRegistration, admin_site)
        self.ssi_admin = StudentSubjectInterestAdmin(StudentSubjectInterest, admin_site)

    def search(self, model_admin, model, term):
        queryset, _duplicates = model_admin.get_search_results(
            self.request, model.objects.all(), term)
        return list(queryset)

    def test_registration_search_by_user(self):
        for term in (self.student.username, 'Hermione', 'Grang', 'hjg@'):
            self.assertIn(self.registration,
                          self.search(self.reg_admin, StudentRegistration, term),
                          'searching for %r should find the registration' % term)

    def test_registration_search_by_id(self):
        for term in (self.registration.id, self.section.id, self.subject.id,
                     self.student.id):
            self.assertIn(self.registration,
                          self.search(self.reg_admin, StudentRegistration, str(term)))

    def test_registration_search_by_class_title(self):
        # Titles are still matched anywhere in the string, not just at the start.
        self.assertIn(self.registration,
                      self.search(self.reg_admin, StudentRegistration, 'Potion'))

    def test_interest_search(self):
        for term in ('Hermione', 'Grang', 'Potion', str(self.interest.id),
                     str(self.subject.id), str(self.student.id)):
            self.assertIn(self.interest,
                          self.search(self.ssi_admin, StudentSubjectInterest, term),
                          'searching for %r should find the interest' % term)

    def test_non_numeric_terms_do_not_error(self):
        """The `=` ID lookups must not blow up on non-numeric search terms."""
        for term in ('not a number', "quotes' and \"quotes\"", '12abc'):
            self.assertEqual(
                [], self.search(self.reg_admin, StudentRegistration, term))
            self.assertEqual(
                [], self.search(self.ssi_admin, StudentSubjectInterest, term))

    def test_list_select_related_covers_displayed_relations(self):
        """Every related object shown in the changelist should be prefetched."""
        for field in ('user', 'relationship', 'section', 'section__parent_class'):
            self.assertIn(field, self.reg_admin.list_select_related)
        for field in ('user', 'subject'):
            self.assertIn(field, self.ssi_admin.list_select_related)
