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

from esp.customforms.models import Form
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ProgramModule
from esp.program.modules.base import ProgramModuleObj
from esp.survey.models import Survey, Question, QuestionType
from esp.tagdict.models import Tag
from esp.users.models import ESPUser

import json

class AllViewsTest(ProgramFrameworkTest):
    def setUp(self):
        # Set up the program framework and randomly schedule classes
        super(AllViewsTest, self).setUp(modules = ProgramModule.objects.all())

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
            'perms': u'',
            'link_id': -1,
            'success_url': '/formsuccess.html',
            'success_message': 'Thank you!',
            'anonymous': False,
            'pages': [{
                'parent_id': -1,
                'sections': [{
                    'fields': [
                        {'data': {'field_type': 'textField', 'question_text': 'ShortText', 'seq': 0, 'required': True, 'parent_id': -1, 'attrs':{'correct_answer': 'Smart', 'charlimits': '0,100'}, 'help_text': 'Instructions'}},
                        {'data': {'field_type': 'phone', 'question_text': 'Your phone no.', 'seq': 1, 'required': True, 'parent_id': -1, 'attrs': {}, 'help_text': u''}},
                        {'data': {'field_type': 'gender', 'question_text': 'Your gender', 'seq': 2, 'required': True, 'parent_id': -1, 'attrs': {}, 'help_text': u''}},
                        {'data': {'field_type': 'radio', 'question_text': 'Choose an option', 'seq': 3, 'required': True, 'parent_id': -1, 'attrs': {'correct_answer': '1', 'options': 'A|B|C|'}, 'help_text': u''}},
                        {'data': {'field_type': 'boolean', 'question_text': 'True/false', 'seq': 4, 'required': True, 'parent_id': -1, 'attrs': {}, 'help_text':u''}},
                        {'data': {'field_type': 'textField', 'question_text': 'NonRequired', 'seq': 5, 'required': False, 'parent_id': -1, 'attrs': {'correct_answer': u'', 'charlimits': ','}, 'help_text': u''}}
                    ],
                'data': {'help_text': u'', 'question_text': u'', 'seq': 0}
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

        # Set up credit card test keys
        settings.STRIPE_CONFIG = {
            'secret_key': 'sk_test_4eC39HqLyjWDarjtT1zdp7dc',
            'publishable_key': 'pk_test_TYooMQauvdEDq54NiTphI7jx',
        }
        settings.CYBERSOURCE_CONFIG = {
            'post_url': 'https://apitest.cybersource.com/pts/v2/payments',
            'merchant_id': 'test',
        }

    def testAllViews(self):
        # Check all views of all modules
        failed_modules = []
        cls = self.program.classes()[0]
        cls_id = str(cls.id)
        sec = cls.get_sections()[0]
        sec_id = str(sec.id)
        event = self.program.getTimeSlots()[0]
        event_id = str(event.id)
        for tl in ['learn', 'teach', 'admin', 'volunteer']:
            modules = self.program.getModules(tl = tl)
            for module in modules:
                views = module.get_all_views()
                for view in views:
                    self.program.classes()[0].get_sections()[0].preregister_student(self.adminUser)
                    # Some views are expecting an "extra" argument; some are expecting "GET" variables; some are expecting "POST" variables
                    try:
                        print("GET")
                        response = self.client.get('/' + tl + '/' + self.program.getUrlBase() + '/' + view + '?cls=' + cls_id + '&clsid=' + cls_id + '&name=Admin&username=admin')
                        if response.status_code in [200, 302]:
                            continue
                    except Exception, e:
                        print(e)
                    try:
                        print("Extra Class")
                        response = self.client.get('/' + tl + '/' + self.program.getUrlBase() + '/' + view + '/' + cls_id + '?student=' + self.adminUser.id)
                        if response.status_code in [200, 302]:
                            continue
                    except Exception, e:
                        print(e)
                    try:
                        print("Extra Section")
                        response = self.client.get('/' + tl + '/' + self.program.getUrlBase() + '/' + view + '/' + sec_id)
                        if response.status_code in [200, 302]:
                            continue
                    except Exception, e:
                        print(e)
                    try:
                        print("Extra Event")
                        response = self.client.get('/' + tl + '/' + self.program.getUrlBase() + '/' + view + '/' + event_id)
                        if response.status_code in [200, 302]:
                            continue
                    except Exception, e:
                        print(e)
                    try:
                        print("POST1")
                        self.program.classes()[0].get_sections()[0].unpreregister_student(self.adminUser)
                        response = self.client.post('/' + tl + '/' + self.program.getUrlBase() + '/' + view, {'class_id': cls_id,  'section_id': sec_id, 'json_data': '{}'})
                        if response.status_code in [200, 302]:
                            continue
                    except Exception, e:
                        print(e)
                    try:
                        print("POST2")
                        response = self.client.post('/' + tl + '/' + self.program.getUrlBase() + '/' + view, {'json_data': '{"interested": [1, 5, 3, 9], "not_interested": [4, 6, 10]}'})
                        if response.status_code in [200, 302]:
                            continue
                    except Exception, e:
                        print(e)
                    try:
                        print("POST3")
                        response = self.client.post('/' + tl + '/' + self.program.getUrlBase() + '/' + view, {'json_data': '{"' + event_id + '": {}}'})
                        if response.status_code in [200, 302]:
                            continue
                    except Exception, e:
                        print(e)
                    failed_modules.append((module, view))

        # Check if any failed
        self.assertTrue(len(failed_modules) == 0, '\n'.join(['The "' + view + '" view from the "' + module.module.handler + '" module is broken.' for (module, view) in failed_modules]))
