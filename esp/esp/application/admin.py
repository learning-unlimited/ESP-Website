__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
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

from django.contrib import admin
from django.utils import html

from esp.admin import admin_site

from esp.program.models import ClassSubject
from esp.formstack.objects import get_forms_for_api_key, get_form_by_id
from esp.application.models import FormstackAppSettings, FormstackStudentProgramApp, FormstackStudentClassApp

from esp.utils.admin_user_search import default_user_search

class FormstackAppSettingsAdmin(admin.ModelAdmin):
    fields = ['program', 'api_key', 'forms_for_api_key',
              'form_id', 'form_fields',
              'username_field', 'coreclass_fields',
              'autopopulated_fields', 'teacher_view_template',
              'finaid_form_id', 'finaid_form_fields',
              'finaid_user_id_field', 'finaid_username_field',
              'app_is_open']
    readonly_fields = ['program', 'forms_for_api_key', 'form_fields', 'finaid_form_fields']
    list_display = ['program', 'app_is_open']
    search_fields = ('program__name',)

    def forms_for_api_key(self, fsas):
        if fsas.api_key == '':
            return ''
        lines = []
        for form in get_forms_for_api_key(fsas.api_key):
            line = '{0}: {1}'.format(form.id, form.name)
            lines.append(line)
        return '<br />'.join(map(html.escape, lines))
    forms_for_api_key.allow_tags = True

    def form_fields(self, fsas):
        if fsas.api_key == '' or fsas.form_id is None:
            return ''
        lines = []
        form = get_form_by_id(fsas.form_id, fsas.api_key)
        for field in form.field_info():
            if field['label']:
                line = '{0}: {1}'.format(field['id'], field['label'])
                lines.append(line)
        return '<br />'.join(map(html.escape, lines))
    form_fields.allow_tags = True

    def finaid_form_fields(self, fsas):
        if fsas.api_key == '' or fsas.finaid_form_id is None:
            return ''
        lines = []
        form = get_form_by_id(fsas.finaid_form_id, fsas.api_key)
        for field in form.field_info():
            if field['label']:
                line = '{0}: {1}'.format(field['id'], field['label'])
                lines.append(line)
        return '<br />'.join(map(html.escape, lines))
    finaid_form_fields.allow_tags = True

admin_site.register(FormstackAppSettings, FormstackAppSettingsAdmin)

class FormstackStudentClassAppInline(admin.TabularInline):
    model = FormstackStudentClassApp
    fields = ['student_preference', 'subject',
              'teacher_rating', 'teacher_ranking', 'teacher_comment']
    readonly_fields = ['student_preference', 'subject']
    max_num = 0

class FormstackStudentProgramAppAdmin(admin.ModelAdmin):
    fields = ['submission_id', 'program', 'user',
              'admin_status', 'admin_comment',
              'admissions_pretty',
              'responses_pretty']
    readonly_fields = ['submission_id', 'program', 'user',
                       'admissions_pretty',
                       'responses_pretty']
    list_display = ['submission_id', 'program', 'user',
                    'admin_status', 'admin_comment',
                    'choices_pretty', 'admissions_pretty']
    list_editable = ['admin_status']
    list_filter = ['admin_status', 'program']
    search_fields = default_user_search()

    def choices_pretty(self, app):
        lines = []
        for pair in app.choices().items():
            line = '{0}: {1}'.format(*pair)
            lines.append(line)
        return '<br />'.join(map(html.escape, lines))
    choices_pretty.allow_tags = True
    choices_pretty.short_description = 'Class choices'

    def responses_pretty(self, app):
        lines = []
        for pair in app.get_responses():
            line = '{0}: {1}'.format(*pair)
            lines.append(line)
        return '<br />'.join(map(html.escape, lines))
    responses_pretty.allow_tags = True
    responses_pretty.short_description = 'Responses'

    def admissions_pretty(self, app):
        lines = []
        cls = app.admitted_to_class()
        if cls is not None:
            line = 'Admitted: {0}'.format(cls)
            lines.append(line)
        for cls in app.waitlisted_to_class():
            line = 'Waitlisted: {0}'.format(cls)
            lines.append(line)
        return '<br />'.join(map(html.escape, lines))
    admissions_pretty.allow_tags = True
    admissions_pretty.short_description = 'Admission status'

    inlines = [
        FormstackStudentClassAppInline,
        ]

admin_site.register(FormstackStudentProgramApp, FormstackStudentProgramAppAdmin)

class FormstackStudentClassAppAdmin(admin.ModelAdmin):
    fields = ['user', 'student_preference', 'subject',
              'admin_status', 'admin_comment',
              'teacher_rating', 'teacher_ranking', 'teacher_comment',
              'admissions_pretty',
              'responses_pretty']
    readonly_fields = ['user', 'student_preference', 'subject',
                       'admin_status', 'admin_comment',
                       'admissions_pretty',
                       'responses_pretty']
    list_display = ['user', 'student_preference', 'subject',
                    'admin_status', 'admin_comment',
                    'teacher_rating', 'teacher_ranking', 'teacher_comment',
                    'admissions_pretty']
    list_display_links = ['user']
    list_filter = ['app__admin_status', 'subject', 'subject__parent_program', 'student_preference']
    search_fields = default_user_search('app__user') + ['subject__title', 'subject__id']

    def user(self, classapp):
        return classapp.app.user

    def admin_status(self, classapp):
        return classapp.app.get_admin_status_display()

    def admin_comment(self, classapp):
        return classapp.app.admin_comment

    def admitted_to_class(self, classapp):
        return classapp.app.admitted_to_class()

    def responses_pretty(self, classapp):
        lines = []
        for pair in classapp.get_responses():
            line = '{0}: {1}'.format(*pair)
            lines.append(line)
        return '<br />'.join(map(html.escape, lines))
    responses_pretty.allow_tags = True
    responses_pretty.short_description = 'Responses'

    def admissions_pretty(self, classapp):
        lines = []
        cls = classapp.app.admitted_to_class()
        if cls is not None:
            line = 'Admitted: {0}'.format(cls)
            lines.append(line)
        for cls in classapp.app.waitlisted_to_class():
            line = 'Waitlisted: {0}'.format(cls)
            lines.append(line)
        return '<br />'.join(map(html.escape, lines))
    admissions_pretty.allow_tags = True
    admissions_pretty.short_description = 'Admission status'

    actions = ['admit', 'unadmit', 'waitlist']

    def admit(self, request, queryset):
        for classapp in queryset:
            classapp.admit()
    admit.short_description = 'Admit students'

    def unadmit(self, request, queryset):
        for classapp in queryset:
            classapp.unadmit()
    unadmit.short_description = 'Un-admit students'

    def waitlist(self, request, queryset):
        for classapp in queryset:
            classapp.waitlist()
    waitlist.short_description = 'Waitlist students'

admin_site.register(FormstackStudentClassApp, FormstackStudentClassAppAdmin)

