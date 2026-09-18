__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2011 by the individual contributors
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

from django.conf import settings
from django.db.models import Q

from esp.customforms.DynamicModel import DynamicModelHandler
from esp.customforms.models import Form
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ProgramModule
from esp.program.modules.base import ProgramModuleObj
from esp.survey.models import Survey, Question, QuestionType
from esp.tagdict.models import Tag
from esp.users.models import ESPUser, PersistentQueryFilter

import json

class AllViewsTest(ProgramFrameworkTest):
    def setUp(self):
        # Set up the program framework and randomly schedule classes
        super().setUp(modules = ProgramModule.objects.all())

        # We don't want to get stuck in registration
        scrmi = self.program.studentclassregmoduleinfo
        scrmi.force_show_required_modules = False
        scrmi.save()

        # So we can confirm registration without errors
        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

        # Create an admin account so we have access to every view
        self.adminUser, created = ESPUser.objects.get_or_create(username='admin', first_name = 'Admin', last_name = 'Admin')
        self.adminUser.set_password('password')
        self.adminUser.makeAdmin()
        self.adminUser.makeRole('Student')
        self.adminUser.makeRole('Teacher')
        self.adminUser.makeRole('Volunteer')

        # Login with the admin account
        self.client.login(username='admin', password='password')

        # Set up a schedule for the program and enroll students
        self.add_user_profiles()
        self.schedule_randomly()
        self.classreg_students()

        # Set up surveys for the program
        (survey1, created) = Survey.objects.get_or_create(name='Test Survey', program=self.program, category='learn')
        (text_qtype, created) = QuestionType.objects.get_or_create(name='yes-no response')
        (number_qtype, created) = QuestionType.objects.get_or_create(name='numeric rating', is_numeric=True, is_countable=True)
        (question_base, created) = Question.objects.get_or_create(survey=survey1, name='Question1', question_type=text_qtype, per_class=False, seq=0)
        (question_perclass, created) = Question.objects.get_or_create(survey=survey1, name='Question2', question_type=text_qtype, per_class=True, seq=1)
        (question_number, created) = Question.objects.get_or_create(survey=survey1, name='Question3', question_type=number_qtype, per_class=True, seq=2)
        (survey2, created) = Survey.objects.get_or_create(name='Test Survey', program=self.program, category='teach')
        (text_qtype, created) = QuestionType.objects.get_or_create(name='yes-no response')
        (number_qtype, created) = QuestionType.objects.get_or_create(name='numeric rating', is_numeric=True, is_countable=True)
        (question_base, created) = Question.objects.get_or_create(survey=survey2, name='Question1', question_type=text_qtype, per_class=False, seq=0)
        (question_perclass, created) = Question.objects.get_or_create(survey=survey2, name='Question2', question_type=text_qtype, per_class=True, seq=1)
        (question_number, created) = Question.objects.get_or_create(survey=survey2, name='Question3', question_type=number_qtype, per_class=True, seq=2)

        # Set up custom forms for the program
        form_data = {
            'title': 'Test Form',
            'perms': '',
            'link_id': -1,
            'success_url': '/formsuccess.html',
            'success_message': 'Thank you!',
            'anonymous': False,
            'pages': [{
                'parent_id': -1,
                'sections': [{
                    'fields': [
                        {'data': {'field_type': 'textField', 'question_text': 'ShortText', 'seq': 0, 'required': True, 'parent_id': -1, 'attrs':{'correct_answer': 'Smart', 'charlimits': '0,100'}, 'help_text': 'Instructions'}},
                        {'data': {'field_type': 'phone', 'question_text': 'Your phone no.', 'seq': 1, 'required': True, 'parent_id': -1, 'attrs': {}, 'help_text': ''}},
                        {'data': {'field_type': 'gender', 'question_text': 'Your gender', 'seq': 2, 'required': True, 'parent_id': -1, 'attrs': {}, 'help_text': ''}},
                        {'data': {'field_type': 'radio', 'question_text': 'Choose an option', 'seq': 3, 'required': True, 'parent_id': -1, 'attrs': {'correct_answer': '1', 'options': 'A|B|C|'}, 'help_text': ''}},
                        {'data': {'field_type': 'boolean', 'question_text': 'True/false', 'seq': 4, 'required': True, 'parent_id': -1, 'attrs': {}, 'help_text':''}},
                        {'data': {'field_type': 'textField', 'question_text': 'NonRequired', 'seq': 5, 'required': False, 'parent_id': -1, 'attrs': {'correct_answer': '', 'charlimits': ','}, 'help_text': ''}}
                    ],
                'data': {'help_text': '', 'question_text': '', 'seq': 0}
                }],
                'seq': 0
            }],
            'link_type': '-1',
            'desc': 'Test'
        }

        response = self.client.post("/customforms/submit/", json.dumps(form_data), content_type='application/json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        form = Form.objects.filter(title='Test Form')[0]
        Tag.setTag(key='learn_extraform_id', value=form.id, target=self.program)
        Tag.setTag(key='teach_extraform_id', value=form.id, target=self.program)
        Tag.setTag(key='quiz_form_id', value=form.id, target=self.program)

        # The second step of each user-search flow (communications, user
        # records, mass deactivation, ...) expects to be handed the id of a
        # filter saved by the first step.  Target a student rather than the
        # admin: deactivatefinal really does deactivate everyone it matches,
        # and losing the admin would break every later view.
        self.user_filter = PersistentQueryFilter.create_from_Q(
            ESPUser, Q(id=self.students[-1].id), 'All views test filter')

        # Set up credit card test keys
        settings.STRIPE_CONFIG = {
            'secret_key': 'sk_test_4eC39HqLyjWDarjtT1zdp7dc',
            'publishable_key': 'pk_test_TYooMQauvdEDq54NiTphI7jx',
        }
        settings.CYBERSOURCE_CONFIG = {
            'post_url': 'https://apitest.cybersource.com/pts/v2/payments',
            'merchant_id': 'test',
        }

    def tearDown(self):
        # clean up custom form
        for form in Form.objects.all():
            dmh = DynamicModelHandler(form)
            dmh.purgeDynModel()
        Tag.unSetTag(key='learn_extraform_id', target=self.program)
        Tag.unSetTag(key='teach_extraform_id', target=self.program)
        Tag.unSetTag(key='quiz_form_id', target=self.program)

        # clean up surveys
        Survey.objects.all().delete()

    def testAllViews(self):
        # Check all views of all modules
        # These are the same for every view, so look them up once rather than
        # re-querying inside the loop.
        cls = self.program.classes()[0]
        cls_id = str(cls.id)
        sec = cls.get_sections()[0]
        sec_id = str(sec.id)
        event = self.program.getTimeSlots()[0]
        event_id = str(event.id)
        user_id = str(self.adminUser.id)
        filter_id = str(self.user_filter.id)

        # The admin-facing modules use the 'manage' module_type; no module uses
        # 'admin', so the previous 'admin' entry here matched nothing.
        for tl in ['learn', 'teach', 'manage', 'volunteer']:
            modules = self.program.getModules(tl = tl)
            for module in modules:
                for view in module.views:
                    # Report each view separately so one broken view neither
                    # hides the others nor requires reading a single blob.
                    with self.subTest(tl = tl, module = module.module.handler, view = view):
                        self.check_view(tl, view, sec, cls_id, sec_id, event_id, user_id, filter_id)

    def check_view(self, tl, view, sec, cls_id, sec_id, event_id, user_id, filter_id):
        """Fail unless one of our candidate requests to this view serves a page."""
        url = '/' + tl + '/' + self.program.getUrlBase() + '/' + view

        # In case the user has been unregistered, reregister them
        sec.preregister_student(self.adminUser)

        def post_fcfs():
            # Mostly used for registering for classes, so unregister for the class in advance
            sec.unpreregister_student(self.adminUser)
            return self.client.post(url, {'class_id': cls_id, 'section_id': sec_id, 'json_data': '{}'})

        # Identifiers that views pick out of the query string by name.  Views
        # that ignore them are unaffected, so every GET below carries all of
        # them; several views want both an extra path segment and a query
        # parameter (accept_student and view_app, for instance).
        query = '&'.join([
            'cls=' + cls_id, 'clsid=' + cls_id, 'name=Admin', 'username=admin',
            'student=' + user_id,       # accept_student, reject_student, view_app
            'sec_id=' + sec_id,         # deletesection
            'filterid=' + filter_id,    # generateList and the other step-2 views
            'last_fetched_index=0',     # ajax_change_log
        ])

        # Try a whole bunch of different requests (because different views have different expectations)
        attempts = [
            # Various GET arguments
            ('GET', lambda: self.client.get(url + '?' + query)),
            # Use a class ID as the extra argument
            ('GET class', lambda: self.client.get(url + '/' + cls_id + '?' + query)),
            # Use a section ID as the extra argument
            ('GET section', lambda: self.client.get(url + '/' + sec_id + '?' + query)),
            # Use an event ID as the extra argument
            ('GET event', lambda: self.client.get(url + '/' + event_id + '?' + query)),
            # Use a user ID as the extra argument
            ('GET user', lambda: self.client.get(url + '/' + user_id + '?' + query)),
            # Various POST data
            ('POST FCFS', post_fcfs),
            # Student lottery POST data
            ('POST lottery', lambda: self.client.post(url, {'json_data': '{"interested": [1, 5, 3, 9], "not_interested": [4, 6, 10]}'})),
            # Different student lottery POST data
            ('POST alt lottery', lambda: self.client.post(url, {'json_data': '{"' + event_id + '": {}}'})),
            # Second step of the user-search flows, which are handed a saved
            # filter id plus whatever their own form collects
            ('POST user search', lambda: self.client.post(url + '?filterid=' + filter_id, {
                'filterid': filter_id,
                'listcount': '1',
                'from': 'test@learningu.org',
                'replyto': 'test@learningu.org',
                'subject': 'Test subject',
                'body': 'Test body',
                'message': 'Test message',
                'confirm': 'true',
                'group_name_new': 'All views test group',
                'records': 'attended',
                'section_id': sec_id,
                'type': 'students',
            })),
            # Scheduling AJAX endpoints, which key off an action plus a section
            ('POST ajax', lambda: self.client.post(url, {
                'action': 'removemod',
                'sec': sec_id,
                'cls': sec_id,
                'mod': user_id,
                'comment': 'Test comment',
            })),
        ]

        # Stop as soon as this view properly serves a page (or redirects to another page)
        failures = []
        for label, attempt in attempts:
            try:
                response = attempt()
            except Exception as e:
                # There is no response to read a status code from, so report
                # the exception that the view raised.
                failures.append('%s: raised %s: %s' % (label, type(e).__name__, e))
                continue
            if 200 <= response.status_code < 400:
                return
            failures.append('%s: HTTP %d' % (label, response.status_code))

        self.fail('No request to %s was served:\n  %s' % (url, '\n  '.join(failures)))
