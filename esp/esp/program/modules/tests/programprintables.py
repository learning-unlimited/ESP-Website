from __future__ import absolute_import
from __future__ import print_function
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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
from django.test.client import RequestFactory

from esp.program.tests import ProgramFrameworkTest
from esp.program.models  import ClassSubject
from ..handlers.programprintables import *

class ProgramPrintablesModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        from esp.program.models import Program
        from esp.program.modules.base import ProgramModule, ProgramModuleObj

        # Set up the program -- we want to be sure of these parameters
        kwargs.update({'num_students': 3,})
        super(ProgramPrintablesModuleTest, self).setUp(*args, **kwargs)

        self.add_student_profiles()
        self.schedule_randomly()
        self.classreg_students()

        # Get and remember the instance of this module
        m = ProgramModule.objects.get(handler='ProgramPrintables', module_type='manage')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, m)

        self.factory = RequestFactory()

        self.all_classes_csv_url = '/manage/%s/%s' % (self.program.getUrlBase(), 'all_classes_spreadsheet')

    def _login_admin(self):
        """
        Login admin user
        """
        self.failUnless(self.client.login(username=self.admins[0].username, password='password'), "Failed to log in admin user.")

    def get_response(self, view_name, user_type, list_name):
        #   Log in an administrator
        self._login_admin()

        self.assertTrue(self.client.login(username=self.admins[0].username, password='password'), "Failed to log in admin user.")

        #   Select users to fetch
        response = self.client.get('/manage/%s/%s' % (self.program.getUrlBase(), view_name))
        self.assertEquals(response.status_code, 200)
        post_data = {
            'recipient_type': user_type,
            'base_list': list_name,
            'use_checklist': 0,
        }
        response = self.client.post('/manage/%s/%s' % (self.program.getUrlBase(), view_name), post_data)
        self.assertEquals(response.status_code, 200)
        return response

    def get_userlist_views(self):
        #   Hard-code some views that can be tested using simple teacher/student lists.
        #   Exclude those tested by specialized functions below.
        teacher_views = ['teacherlist', 'teachersbytime', 'teacherschedules']
        student_views = ['studentsbyname', 'emergencycontacts', 'flatstudentschedules', 'studentchecklist', 'student_tickets']
        result = []
        for v in teacher_views:
            result.append((v, 'teachers', 'class_approved'))
        for v in student_views:
            result.append((v, 'students', 'enrolled'))
        return result

    def testAllViewsWithUserList(self):
        #   Specify which basic list of users to use for each printables view.
        view_pairs = self.get_userlist_views()

        #   Test each view in sequence with the appropriate list of users.
        #   Doesn't check correctness; please add separate test functions for that.
        for (view_name, user_type, list_name) in view_pairs:
            self.get_response(view_name, user_type, list_name)

    def testClassRosters(self):
        #   Check that all classes show up on the rosters.
        response = self.get_response('classrosters', 'teachers', 'class_approved')
        self.assertContains(response, '<div class="classtitle">', count=len(self.program.classes()))

    def testSchedules(self):
        response = self.get_response('studentschedules/log', 'students', 'enrolled')
        print(response)
        #   Check that our Latex->PDF schedule generation code runs without error
        response = self.get_response('studentschedules', 'students', 'enrolled')

        #   Check that the output is an actual PDF file
        print((response['Content-Type']))
        self.assertTrue(response['Content-Type'].startswith('application/pdf'))

    def post_schedules(self, extra=''):
        """ Request PDF (or other) schedules for all enrolled students, and
        return the response whatever its status. """
        self._login_admin()
        url = '/manage/%s/studentschedules%s' % (self.program.getUrlBase(), extra)
        return self.client.post(url, {'recipient_type': 'students', 'base_list': 'enrolled', 'use_checklist': 0})

    def test_schedule_rows(self):
        """ Each class row shows the section's times, rooms, code and teachers. """
        from esp.program.models import StudentRegistration
        tex = self.post_schedules('/tex').content.decode('utf8')
        srs = StudentRegistration.valid_objects().filter(
            relationship__name='Enrolled', section__parent_class__parent_program=self.program)
        self.assertTrue(srs.exists())
        for section in set(sr.section for sr in srs):
            if not section.meeting_times.exists():
                continue
            self.assertIn(section.emailcode(), tex)
            for time in section.friendly_times():
                self.assertIn(time, tex)
            for room in section.initial_rooms():
                self.assertIn(room.name, tex)
            for name in section.parent_class.getTeacherNamesWithPronouns():
                self.assertIn(name, tex)

    def test_schedule_page_overflow(self):
        """ Schedules whose content runs past its page are refused, naming
        the students, rather than printed wrong. """
        from esp.tagdict.models import Tag
        too_long = '\n\n'.join('Line %d of a very long note.' % i for i in range(80))
        for barcode in (True, False):
            fields = ['username', 'codes'] + (['barcode'] if barcode else [])
            Tag.setTag('student_schedule_format', target=self.program, value=json.dumps(fields))
            #   Fine as it is
            Tag.setTag('student_schedule_pretext', target=self.program, value='Short.')
            Tag.setTag('student_schedule_posttext', target=self.program, value='Short.')
            response = self.post_schedules()
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response['Content-Type'].startswith('application/pdf'))
            #   Too much text above or below the schedule
            for tag in ('student_schedule_pretext', 'student_schedule_posttext'):
                Tag.setTag(tag, target=self.program, value=too_long)
                response = self.post_schedules()
                self.assertEqual(response.status_code, 500)
                self.assertContains(response, 'student schedules run past', status_code=500)
                self.assertContains(response, self.students[0].username, status_code=500)
                #   One student's schedule (e.g. printed onsite) comes out anyway
                request = self.factory.get('/')
                request.session = {}
                response = ProgramPrintables.get_student_schedules(request, [self.students[0]], self.program, 'pdf')
                self.assertTrue(response['Content-Type'].startswith('application/pdf'))
                Tag.setTag(tag, target=self.program, value='Short.')

    def test_check_schedule_pages(self):
        students = self.students[:3]

        def log(starts, total):
            #   starts: the page each student's page starts landed on
            return ''.join('ESPSCHEDMARK %d:%d:%d\n' % (i, k, page)
                           for i, pages in enumerate(starts) for k, page in enumerate(pages)
                           ) + 'ESPSCHEDPAGES %d\n' % total

        check_schedule_pages(log([(1, 2), (3, 4), (5, 6)], 6), students, pages_per_student=2)
        #   The second student's first page spilled, pushing everything after
        #   it back a page; only that student is blamed
        with self.assertRaises(SchedulePageOverflow) as cm:
            check_schedule_pages(log([(1, 2), (3, 5), (6, 7)], 7), students, pages_per_student=2)
        self.assertIn('1 of 3', str(cm.exception))
        self.assertIn('%s): first page' % students[1].username, str(cm.exception))
        self.assertNotIn(students[0].username, str(cm.exception))
        self.assertNotIn(students[2].username, str(cm.exception))
        #   The last student's schedule page spilled: only the total shows it
        with self.assertRaises(SchedulePageOverflow) as cm:
            check_schedule_pages(log([(1, 2), (3, 4), (5, 6)], 7), students, pages_per_student=2)
        self.assertIn('%s): schedule page' % students[2].username, str(cm.exception))

    def test_latex_printables_keep_accented_names(self):
        for student in self.students:
            student.first_name = u'Jos\u00e9'
            student.last_name = u'W\u00f3jcik-Nguy\u1ec5n \u738b'
            student.save()
        for cls in self.program.classes():
            cls.title = u'Caf\u00e9 \u00c9conomie \u0141\u00f3d\u017a \u201cquoted\u201d'
            cls.save()

        tex = self.get_response('studentschedules/tex', 'students', 'enrolled').content.decode('utf8')
        self.assertIn(u'Jos\u00e9 W\u00f3jcik-Nguyen ?', tex)
        response = self.get_response('studentschedules', 'students', 'enrolled')
        self.assertTrue(response['Content-Type'].startswith('application/pdf'))

        for query in ('', '?sort_name_list=timeblock'):
            response = self.client.get('/manage/%s/coursecatalog%s' % (self.program.getUrlBase(), query))
            self.assertTrue(response['Content-Type'].startswith('application/pdf'), response.content[-1500:])
        # Certificates need media/latex_media/letterhead.pdf; dev and CI copies
        # get a blank one from deploy/make_blank_letterhead.sh.
        base = '/manage/%s/certificate' % self.program.getUrlBase()
        response = self.client.get('%s/tex?userid=%d' % (base, self.students[0].id))
        self.assertIn(u'Jos\u00e9 W\u00f3jcik-Nguyen ?', response.content.decode('utf8'))
        response = self.client.get('%s?userid=%d' % (base, self.students[0].id))
        self.assertTrue(response['Content-Type'].startswith('application/pdf'), response.content[-1500:])

    def test_all_classes_spreadsheet_loads(self):
        """
        User must be admin to access the spreadsheet via GET method and that the field selection template
        and form is used.
        """
        self._login_admin()
        response = self.client.get(self.all_classes_csv_url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/programprintables/all_classes_select_fields.html')

    def test_all_classes_spreadsheet_invalid_post(self):
        """
        User must be admin to POST to all_classes_spreadsheet. Responses mimetype must be text/csv
        """
        self._login_admin()

        #Test empty form
        response = self.client.post(self.all_classes_csv_url)
        self.assertEquals(response.status_code, 200)
        self.assertFormError(response, 'form', 'subject_fields', 'This field is required.')

        #Test invalid fieldname
        self.client.post(self.all_classes_csv_url, {'subject_fields':['invalid_field']})
        self.assertFormError(response, 'form', 'subject_fields', 'This field is required.')

    def test_all_classes_spreadsheet_valid_post(self):
        """
        User must be admin to POST to all_classes_spreadsheet. Responses mimetype must be text/csv
        """
        self._login_admin()
        exclude_fields = ['session_count']
        #select all valid fields
        post_data = {'subject_fields':[field.name for field in ClassSubject._meta.fields if field.name not in exclude_fields]}

        response = self.client.post(self.all_classes_csv_url, post_data)
        self.assertEquals(response.status_code, 200)

        self.assertEquals(
            response.get('Content-Disposition'),
            "attachment; filename=all_classes.csv"
        )


class TestAllClassesSelectionForm(ProgramFrameworkTest):

    def test_empty_field_selection(self):
        """Ensure that at least one selection is required"""
        form = AllClassesSelectionForm(program=self.program)
        self.assertFalse(form.is_valid())

    def test_invalid_field_selection(self):
        """Ensure that form does not accept invalid field names"""
        params = {'subject_fields':['an_invalid_field_name']}
        form = AllClassesSelectionForm(self.program, params)
        self.assertFalse(form.is_valid())

    def test_class_subject_fields_accepted(self):
        """Ensure that field names of ClassSubject are accepted, except the
        ones the form deliberately leaves out"""
        excluded = AllClassesFieldConverter.exclude_fields
        params = {'subject_fields': [field.name for field in ClassSubject._meta.fields if field.name not in excluded]}
        form = AllClassesSelectionForm(self.program, params)
        self.assertTrue(form.is_valid())


class TestAllClassesFieldConverter(ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        super(TestAllClassesFieldConverter, self).setUp(*args, **kwargs)
        self.class_subjects = ClassSubject.objects.all()
        self.class_subject_fieldnames = [field.name for field in ClassSubject._meta.fields]
        self.converter = AllClassesFieldConverter(self.program)

    def test_fieldvalue_fakefield(self):
        """
        An invalid field should raise a ValueError
        """
        class_subject = self.class_subjects[0]
        self.assertRaises(ValueError, self.converter.fieldvalue, *[class_subject, 'fake_field'])

    def test_class_subject_fields_accepted(self):
        """
        Verifies that the fields on a class subject instance are formatted
        by the converter.
        """
        class_subject = self.class_subjects[0]
        for fieldname in self.class_subject_fieldnames:
            self.assertEquals(self.converter.fieldvalue(class_subject, fieldname), \
                              getattr(class_subject, fieldname))

    def test_class_subject_teachers_format(self):
        class_subject = self.class_subjects[0]

        teacher_names = [t.name() for t in class_subject.get_teachers()]
        formatted_teachers = [t.strip() for t in self.converter. \
                              fieldvalue(class_subject, 'teachers').split(',')]
        self.assertEquals(set(formatted_teachers), set(teacher_names))

    def test_class_times_format(self):
        class_subject = self.class_subjects[0]
        formatted_times = self.converter.fieldvalue(class_subject, 'times')

        for t in class_subject.friendly_times():
            self.assertIn(t, formatted_times)

    def test_class_rooms_format(self):
        class_subject = self.class_subjects[0]
        formatted_rooms = self.converter.fieldvalue(class_subject, 'rooms')

        for t in class_subject.prettyrooms():
            self.assertIn(t, formatted_rooms)

