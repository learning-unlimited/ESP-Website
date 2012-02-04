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
  Email: web-team@lists.learningu.org
"""

from django.contrib import admin
from django.db.models import ManyToManyField

from esp.admin import admin_site

from esp.program.models import ProgramModule, ArchiveClass, Program, BusSchedule
from esp.program.models import TeacherParticipationProfile, SATPrepRegInfo, RegistrationProfile
from esp.program.models import TeacherBio, FinancialAidRequest, SplashInfo
from esp.program.models import VolunteerRequest, VolunteerOffer

from esp.program.models import BooleanToken, BooleanExpression, ScheduleConstraint, ScheduleTestOccupied, ScheduleTestCategory, ScheduleTestSectionList

from esp.program.models import RegistrationType, StudentRegistration

from esp.program.models import ProgramCheckItem, ClassSection, ClassSubject, ClassCategories, ClassSizeRange
from esp.program.models import StudentApplication, StudentAppQuestion, StudentAppResponse, StudentAppReview


class ProgramModuleAdmin(admin.ModelAdmin):
    list_display = ('link_title', 'admin_title', 'handler')
    search_fields = ['link_title', 'admin_title', 'handler']
admin_site.register(ProgramModule, ProgramModuleAdmin)
    
class ArchiveClassAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'year', 'date', 'category', 'program', 'teacher')
    search_fields = ['description', 'title', 'program', 'teacher', 'category']
    pass
admin_site.register(ArchiveClass, ArchiveClassAdmin)

class ProgramAdmin(admin.ModelAdmin):
    class Media:
        css = { 'all': ( 'styles/admin.css', ) }
    formfield_overrides = { ManyToManyField: { 'widget': admin.widgets.FilteredSelectMultiple(verbose_name='', is_stacked=False) } }
    # formfield_overrides will work once we move past Django r9760.
    # At that time we should cut out formfield_for_dbfield.
    def formfield_for_dbfield(self, db_field, **kwargs):
        if isinstance( db_field, ManyToManyField ):
            kwargs['widget'] = admin.widgets.FilteredSelectMultiple(verbose_name='', is_stacked=False)
        return super(ProgramAdmin, self).formfield_for_dbfield(db_field,**kwargs)
admin_site.register(Program, ProgramAdmin)

admin_site.register(BusSchedule)
admin_site.register(TeacherParticipationProfile)

class SATPrepRegInfoAdmin(admin.ModelAdmin):
    list_display = ('user', 'program')
    #list_filter = ('program',)
    search_fields = ['user__username']
    pass
admin_site.register(SATPrepRegInfo, SATPrepRegInfoAdmin)

class RegistrationProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'contact_user', 'program')
    pass
admin_site.register(RegistrationProfile, RegistrationProfileAdmin)
    
class TeacherBioAdmin(admin.ModelAdmin):
    list_display = ('user', 'program', 'slugbio')
    search_fields = ['user__username', 'slugbio', 'bio']

admin_site.register(TeacherBio, TeacherBioAdmin)
    
admin_site.register(FinancialAidRequest)

class Admin_SplashInfo(admin.ModelAdmin):
    list_display = (
        'student',
        'program',
    )
    search_fields = [
        'student__username',
        'student__last_name',
        'student__email',
    ]
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
admin_site.register(ScheduleConstraint, Admin_ScheduleConstraint)

class ScheduleTestOccupiedAdmin(admin.ModelAdmin):
    list_display = ('timeblock', 'expr', 'seq', subclass_instance_type, 'text')
admin_site.register(ScheduleTestOccupied, ScheduleTestOccupiedAdmin)

class ScheduleTestCategoryAdmin(admin.ModelAdmin):
    list_display = ('timeblock', 'category', 'expr', 'seq', subclass_instance_type, 'text')
admin_site.register(ScheduleTestCategory, ScheduleTestCategoryAdmin)

class ScheduleTestSectionListAdmin(admin.ModelAdmin):
    list_display = ('timeblock', 'section_ids', 'expr', 'seq', subclass_instance_type, 'text')
admin_site.register(ScheduleTestSectionList, ScheduleTestSectionListAdmin)

admin_site.register(VolunteerRequest)
admin_site.register(VolunteerOffer)

## class_.py

class ProgramCheckItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'program')
admin_site.register(ProgramCheckItem, ProgramCheckItemAdmin)

class Admin_RegistrationType(admin.ModelAdmin):
    list_display = ('name', 'category', )
admin_site.register(RegistrationType, Admin_RegistrationType)

def expire_student_registrations(modeladmin, request, queryset):
    for reg in queryset:
        reg.expire()
class StudentRegistrationAdmin(admin.ModelAdmin):
    list_display = ('id', 'section', 'user', 'relationship', 'start_date', 'end_date', )
    actions = [ expire_student_registrations, ]
admin_site.register(StudentRegistration, StudentRegistrationAdmin)

def sec_classrooms(obj):
    return list(set([(x.name, str(x.num_students) + " students") for x in obj.classrooms()]))
def sec_teacher_optimal_capacity(obj):
    return (obj.parent_class.class_size_max if obj.parent_class.class_size_max else obj.parent_class.class_size_optimal)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'friendly_times', 'status', 'duration', 'max_class_capacity', sec_teacher_optimal_capacity, sec_classrooms)
    list_display_links = ('title',)
    list_filter = ['status']
    pass
admin_site.register(ClassSection, SectionAdmin)


class SubjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'parent_program', 'category')
    list_display_links = ('title',)
    search_fields = ['class_info', 'anchor__friendly_name']
admin_site.register(ClassSubject, SubjectAdmin)

class Admin_ClassCategories(admin.ModelAdmin):
     list_display = ('category', 'symbol', 'seq', )
admin_site.register(ClassCategories, Admin_ClassCategories)

class Admin_ClassSizeRange(admin.ModelAdmin):
     list_display = ('program', 'range_min', 'range_max', )
admin_site.register(ClassSizeRange, Admin_ClassSizeRange)

## app_.py

admin_site.register(StudentApplication)

class Admin_StudentAppQuestion(admin.ModelAdmin):
    list_display = (
        'program',
        'subject',
        'question',
    )
    list_display_links = ('program', 'subject', )
    list_filter = ('subject__parent_program', 'program', )
admin_site.register(StudentAppQuestion, Admin_StudentAppQuestion)

class Admin_StudentAppResponse(admin.ModelAdmin):
    list_display = (
        'question',
        'response',
        'complete',
    )
    list_display_links = list_display
    list_filter = ('question__subject__parent_program', 'question__program', )
admin_site.register(StudentAppResponse, Admin_StudentAppResponse)

class Admin_StudentAppReview(admin.ModelAdmin):
    list_display = (
        'reviewer',
        'date',
        'score',
        'comments',
    )
admin_site.register(StudentAppReview, Admin_StudentAppReview)
