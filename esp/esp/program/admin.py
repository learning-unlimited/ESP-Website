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

from esp.admin import admin_site

from esp.program.models import ProgramModule, ArchiveClass, Program
from esp.program.models import RegistrationProfile
from esp.program.models import TeacherBio, FinancialAidRequest, SplashInfo
from esp.program.models import VolunteerRequest, VolunteerOffer

from esp.program.models import BooleanToken, BooleanExpression, ScheduleConstraint, ScheduleTestOccupied, ScheduleTestCategory, ScheduleTestSectionList

from esp.program.models import RegistrationType, StudentRegistration, StudentSubjectInterest, PhaseZeroRecord

from esp.program.models import ClassSection, ClassSubject, ClassCategories, ClassSizeRange
from esp.program.models import StudentApplication, StudentAppQuestion, StudentAppResponse, StudentAppReview

from esp.program.models import ClassFlag, ClassFlagType

from esp.accounting.models import FinancialAidGrant

from esp.utils.admin_user_search import default_user_search

class ProgramModuleAdmin(admin.ModelAdmin):
    list_display = ('link_title', 'admin_title', 'handler')
    search_fields = ['link_title', 'admin_title', 'handler']
admin_site.register(ProgramModule, ProgramModuleAdmin)

class ArchiveClassAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'year', 'date', 'category', 'program', 'teacher')
    search_fields = ['id', 'description', 'title', 'program', 'teacher', 'category']
    pass
admin_site.register(ArchiveClass, ArchiveClassAdmin)

class ProgramAdmin(admin.ModelAdmin):
    class Media:
        css = { 'all': ( 'styles/admin.css', ) }
    list_display = ('id', 'name', 'url', 'director_email', 'grade_min', 'grade_max',)
    filter_horizontal = ('program_modules', 'class_categories', 'flag_types',)
    search_fields = ('name', )
admin_site.register(Program, ProgramAdmin)

class RegistrationProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'contact_user', 'contact_guardian', 'contact_emergency', 'program', 'last_ts')
    search_fields = default_user_search() + ['contact_user__first_name', 'contact_user__last_name',
                                            'contact_guardian__first_name', 'contact_guardian__last_name',
                                            'contact_emergency__first_name', 'contact_emergency__last_name']
    list_filter = ('program', )
    date_hierarchy = 'last_ts'

    def lookup_allowed(self, key, value):
        return True

admin_site.register(RegistrationProfile, RegistrationProfileAdmin)

class TeacherBioAdmin(admin.ModelAdmin):
    list_display = ('user', 'program', 'slugbio')
    search_fields = default_user_search() + ['slugbio', 'bio']

admin_site.register(TeacherBio, TeacherBioAdmin)

class FinancialAidGrantInline(admin.TabularInline):
    model = FinancialAidGrant
    extra = 1
    max_num = 1
    verbose_name_plural = 'Financial aid grant - enter 100 in "Percent" field to waive entire cost'

class FinancialAidRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'approved', 'reduced_lunch', 'program', 'household_income', 'extra_explaination')
    search_fields = default_user_search() + ['id', 'program__url']
    list_filter = ['program']
    inlines = [FinancialAidGrantInline,]
    actions = ['approve', ]

    def save_related(self, request, form, formsets, change):
        form.save_m2m()
        obj = form.instance
        # get the financial aid grant formset
        formset = formsets[0]
        # if we want to delete or change an existing grant, just save like normal
        if formset[0].cleaned_data.get('DELETE') or obj.approved:
            self.save_formset(request, form, formset, change=change)
        else:
            # if we want to add a grant, use approve() instead
            instance = formset.save(commit=False)[0]
            obj.approve(instance.amount_max_dec, instance.percent)
            formset.save_m2m()
            self.message_user(request, "Request successfully approved.")

    def approve(self, request, queryset):
        num_approved = len([req for req in queryset if not req.approved])
        for req in queryset:
            req.approve()
        self.message_user(request, "%s request(s) successfully approved." % num_approved)
    approve.short_description = "Approve selected financial aid requests for 100%%"
admin_site.register(FinancialAidRequest, FinancialAidRequestAdmin)

class Admin_SplashInfo(admin.ModelAdmin):
    list_display = (
        'student',
        'program',
    )
    search_fields = default_user_search('student')
    list_filter = [ 'program', ]
admin_site.register(SplashInfo, Admin_SplashInfo)

## Schedule stuff (wish it was schedule_.py)

def subclass_instance_type(obj):
    return type(obj.subclass_instance())._meta.object_name
subclass_instance_type.short_description = 'Instance type'

class BooleanTokenAdmin(admin.ModelAdmin):
    list_display = ('expr', 'seq', subclass_instance_type, 'text')
    search_fields = ['text']
admin_site.register(BooleanToken, BooleanTokenAdmin)

class BooleanExpressionAdmin(admin.ModelAdmin):
    list_display = ('label', subclass_instance_type, 'num_tokens')
    def num_tokens(self, obj):
        return len(obj.get_stack())
admin_site.register(BooleanExpression, BooleanExpressionAdmin)

class Admin_ScheduleConstraint(admin.ModelAdmin):
    list_display = (
        'program',
        'condition',
        'requirement',
    )
    list_filter = ('program',)
admin_site.register(ScheduleConstraint, Admin_ScheduleConstraint)

class ScheduleTestOccupiedAdmin(admin.ModelAdmin):
    def program(obj):
        return obj.timeblock.program
    list_display = ('timeblock', program, 'expr', 'seq', subclass_instance_type, 'text')
    list_filter = ('timeblock__program',)
admin_site.register(ScheduleTestOccupied, ScheduleTestOccupiedAdmin)

class ScheduleTestCategoryAdmin(admin.ModelAdmin):
    def program(obj):
        return obj.timeblock.program
    list_display = ('timeblock', program, 'category', 'expr', 'seq', subclass_instance_type, 'text')
    list_filter = ('timeblock__program',)
admin_site.register(ScheduleTestCategory, ScheduleTestCategoryAdmin)

class ScheduleTestSectionListAdmin(admin.ModelAdmin):
    def program(obj):
        return obj.timeblock.program
    list_display = ('timeblock', program, 'section_ids', 'expr', 'seq', subclass_instance_type, 'text')
    list_filter = ('timeblock__program',)
admin_site.register(ScheduleTestSectionList, ScheduleTestSectionListAdmin)

class VolunteerOfferInline(admin.StackedInline):
    model = VolunteerOffer
class VolunteerRequestAdmin(admin.ModelAdmin):
    def description(obj):
        return obj.timeslot.description
    def time(obj):
        return obj.timeslot.short_time()
    def date(obj):
        return obj.timeslot.pretty_date()
    list_display = ('id', 'program', description, time, date, 'num_volunteers')
    list_filter = ('program',)
    inlines = [VolunteerOfferInline,]
admin_site.register(VolunteerRequest, VolunteerRequestAdmin)

class VolunteerOfferAdmin(admin.ModelAdmin):
    def program(obj):
        return obj.request.program
    def description(obj):
        return obj.request.timeslot.description
    def time(obj):
        return obj.request.timeslot.short_time()
    def date(obj):
        return obj.request.timeslot.pretty_date()
    list_display = ('id', 'user', 'email', 'name', description, time, date, program, 'confirmed')
    list_filter = ('request__program',)
    search_fields = default_user_search() + ['email', 'name']
admin_site.register(VolunteerOffer, VolunteerOfferAdmin)

## class_.py

class Admin_RegistrationType(admin.ModelAdmin):
    list_display = ('name', 'category', 'displayName', 'description', )
admin_site.register(RegistrationType, Admin_RegistrationType)

def expire_student_registrations(modeladmin, request, queryset):
    for reg in queryset:
        reg.expire()
    modeladmin.message_user(request, "%s registration(s) successfully expired" % len(queryset))

def renew_student_registrations(modeladmin, request, queryset):
    for reg in queryset:
        reg.unexpire()
    modeladmin.message_user(request, "%s registration(s) successfully renewed" % len(queryset))

class StudentRegistrationAdmin(admin.ModelAdmin):
    list_display = ('id', 'section', 'user', 'relationship', 'start_date', 'end_date',)
    actions = [ expire_student_registrations, renew_student_registrations ]
    search_fields = default_user_search() + ['id', 'section__id', 'section__parent_class__title', 'section__parent_class__id']
    list_filter = ['section__parent_class__parent_program', 'relationship']
    date_hierarchy = 'start_date'
admin_site.register(StudentRegistration, StudentRegistrationAdmin)

class StudentSubjectInterestAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'user', 'start_date', 'end_date', )
    actions = [ expire_student_registrations, ]
    search_fields = default_user_search() + ['id', 'subject__id', 'subject__title']
    list_filter = ['subject__parent_program',]
    date_hierarchy = 'start_date'
admin_site.register(StudentSubjectInterest, StudentSubjectInterestAdmin)

def sec_classrooms(obj):
    return "; ".join(list(set([x.name +': ' +  str(x.num_students) + " students" for x in obj.classrooms()])))
def sec_teacher_optimal_capacity(obj):
    return (obj.parent_class.class_size_max if obj.parent_class.class_size_max else obj.parent_class.class_size_optimal)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('emailcode', 'title', 'friendly_times', 'status', 'duration', 'max_class_capacity', sec_teacher_optimal_capacity, sec_classrooms)
    list_display_links = ('title',)
    list_filter = ['status', 'parent_class__parent_program']
    search_fields = ['=id', '=parent_class__id', 'parent_class__title', 'parent_class__class_info', 'resourceassignment__resource__name']
admin_site.register(ClassSection, SectionAdmin)

class SectionInline(admin.TabularInline):
    model = ClassSection
    fields = ('status','meeting_times', 'prettyrooms')
    readonly_fields = ('meeting_times', 'prettyrooms')
    can_delete = False

class SubjectAdmin(admin.ModelAdmin):
    list_display = ('category', 'id', 'title', 'parent_program',
                    'pretty_teachers')
    list_display_links = ('title',)
    search_fields = default_user_search('teachers') + ['class_info', 'title', 'id']
    exclude = ('teachers',)
    readonly_fields = ('timestamp',)
    list_filter = ('parent_program', 'category')
    inlines = (SectionInline,)
    fieldsets = (
        (None, {
            'fields': ('title', 'parent_program', 'timestamp', 'category',
                       'class_info', 'message_for_directors',
                       'directors_notes', 'purchase_requests')
        }),
        ('Registration Info', {
            'classes': ('collapse',),
            'fields': (('grade_min', 'grade_max'), 'allow_lateness', 'prereqs',
                       'hardness_rating')
        }),
        ('Scheduling Info', {
            'classes': ('collapse',),
            'fields': ('requested_room', 'requested_special_resources',
                       ('allowable_class_size_ranges',
                        'optimal_class_size_range'),
                       ('class_size_min', 'class_size_optimal',
                        'class_size_max', 'session_count'))
        }),
        ('Advanced', {'fields': ('schedule', 'custom_form_data')}),
    )
admin_site.register(ClassSubject, SubjectAdmin)

class Admin_ClassCategories(admin.ModelAdmin):
     list_display = ('category', 'symbol', 'seq', )
admin_site.register(ClassCategories, Admin_ClassCategories)

class Admin_ClassSizeRange(admin.ModelAdmin):
     list_display = ('program', 'range_min', 'range_max', )
     list_filter = ('program',)
admin_site.register(ClassSizeRange, Admin_ClassSizeRange)

## app_.py

class StudentAppAdmin(admin.ModelAdmin):
    list_display = ('user','program', 'done')
    search_fields = default_user_search()
    list_filter = ('program',)
admin_site.register(StudentApplication, StudentAppAdmin)

class Admin_StudentAppQuestion(admin.ModelAdmin):
    list_display = (
        'program',
        'subject',
        'question',
    )
    search_fields = ('subject__title', 'subject__id')
    list_display_links = ('program', 'subject', )
    list_filter = ('subject__parent_program', 'program', )
admin_site.register(StudentAppQuestion, Admin_StudentAppQuestion)

class Admin_StudentAppResponse(admin.ModelAdmin):
    list_display = (
        'question',
        'response',
        'complete',
    )
    readonly_fields = ('question',)
    list_display_links = list_display
    search_fields = default_user_search('question__studentapplication__user')
    list_filter = ('question__subject__parent_program', 'question__program', )
admin_site.register(StudentAppResponse, Admin_StudentAppResponse)

class Admin_StudentAppReview(admin.ModelAdmin):
    list_display = (
        'reviewer',
        'date',
        'score',
        'comments',
    )
    search_fields = default_user_search('reviewer')
    list_filter = ('date',)
admin_site.register(StudentAppReview, Admin_StudentAppReview)

class ClassFlagTypeAdmin(admin.ModelAdmin):
    list_display = ('name','show_in_scheduler','show_in_dashboard')
    search_fields = ['name']
    list_filter = ['program']
admin_site.register(ClassFlagType, ClassFlagTypeAdmin)

class ClassFlagAdmin(admin.ModelAdmin):
    list_display = ('flag_type','subject','comment', 'created_by', 'modified_by')
    readonly_fields = ['modified_by', 'modified_time', 'created_by', 'created_time']
    search_fields = default_user_search('modified_by') + default_user_search('created_by') + ['flag_type__name', 'flag_type__id', 'subject__id', 'subject__title', 'subject__parent_program__url', 'comment']
    list_filter = ['subject__parent_program','flag_type']
admin_site.register(ClassFlag, ClassFlagAdmin)

class PhaseZeroRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'display_user', 'program')
    search_fields = ['user__username']
    list_filter = ['program']
admin_site.register(PhaseZeroRecord, PhaseZeroRecordAdmin)
