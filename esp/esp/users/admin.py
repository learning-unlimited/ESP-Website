from django.contrib import admin
from esp.admin import admin_site
from django import forms
from django.db import models
from esp.users.models.forwarder import UserForwarder
from esp.users.models import UserAvailability, ContactInfo, StudentInfo, TeacherInfo, GuardianInfo, EducatorInfo, ZipCode, ZipCodeSearches, K12School, ESPUser, Record, Permission, GradeChangeRequest
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from esp.utils.admin_user_search import default_user_search
import datetime

class UserForwarderAdmin(admin.ModelAdmin):
    list_display = ('source', 'target')
    search_fields = default_user_search('source') + default_user_search('target')
admin_site.register(UserForwarder, UserForwarderAdmin)

class ZipCodeAdmin(admin.ModelAdmin):
    search_fields = ('=zip_code',)
    list_display = ('zip_code', 'latitude', 'longitude')
admin_site.register(ZipCode, ZipCodeAdmin)

class ZipCodeSearchesAdmin(admin.ModelAdmin):
    def count(obj):
        return len(obj.zipcodes.split(','))
    count.short_description = "Number of zip codes"
    list_display = ('zip_code', 'distance', count)
    search_fields = ('=zip_code__zip_code',)
admin_site.register(ZipCodeSearches, ZipCodeSearchesAdmin)

class UserAvailabilityAdmin(admin.ModelAdmin):
    def parent_program(obj): #because 'event__program' for some reason doesn't want to work...
        return obj.event.program
    list_display = ['id', 'user', 'event', parent_program]
    list_filter = ['event__program', ]
    search_fields = default_user_search()
    ordering = ['-event__program', 'user__username', 'event__start']
admin_site.register(UserAvailability, UserAvailabilityAdmin)

class ESPUserAdmin(UserAdmin):
    #remove the user_permissions from adminpage
    #(since we don't use it)
    #See https://github.com/django/django/blob/stable/1.3.x/django/contrib/auth/admin.py

    from django.utils.translation import ugettext_lazy as _
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('User Roles'), {'fields': ('groups',)}),
        )
admin_site.register(ESPUser, ESPUserAdmin)

class RecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'event', 'program', 'time',]
    list_filter = ['event', 'program', 'time']
    search_fields = default_user_search()
    date_hierarchy = 'time'
admin_site.register(Record, RecordAdmin)

class PermissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'role', 'permission_type','program','start_date','end_date']
    search_fields = default_user_search() + ['permission_type', 'program__url']
    list_filter = ['permission_type', 'program', 'role']
    date_hierarchy = 'start_date'
    actions = [ 'expire', 'renew' ]

    def expire(self, request, queryset):
        rows_updated = queryset.update(end_date=datetime.datetime.now())
        if rows_updated == 1:
            message_bit = "1 permission was"
        else:
            message_bit = "%s permissions were" % rows_updated
        self.message_user(request, "%s successfully expired." % message_bit)
    expire.short_description = "Expire permissions"

    def renew(self, request, queryset):
        rows_updated = queryset.update(end_date=None)
        if rows_updated == 1:
            message_bit = "1 permission was"
        else:
            message_bit = "%s permissions were" % rows_updated
        self.message_user(request, "%s successfully expired." % message_bit)
    renew.short_description = "Renew permissions"

admin_site.register(Permission, PermissionAdmin)

class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'e_mail', 'phone_day', 'address_postal']
    search_fields = default_user_search() + ['e_mail']
admin_site.register(ContactInfo, ContactInfoAdmin)

class UserInfoAdmin(admin.ModelAdmin):
    search_fields = default_user_search()

class StudentInfoAdmin(UserInfoAdmin):
    list_display = ['id', 'user', 'graduation_year', 'getSchool']
    list_filter = ['graduation_year', 'studentrep']
    search_fields = default_user_search()
admin_site.register(StudentInfo, StudentInfoAdmin)

class TeacherInfoAdmin(UserInfoAdmin):
    list_display = ['id', 'user', 'graduation_year', 'from_here', 'college', 'is_graduate_student', 'affiliation']
    search_fields = default_user_search() + ['college']
    list_filter = ('from_here', 'is_graduate_student', 'graduation_year', 'affiliation')
admin_site.register(TeacherInfo, TeacherInfoAdmin)

class GuardianInfoAdmin(UserInfoAdmin):
    list_display = ['id', 'user', 'year_finished', 'num_kids']
    search_fields = default_user_search()
admin_site.register(GuardianInfo, GuardianInfoAdmin)

class EducatorInfoAdmin(UserInfoAdmin):
    search_fields = default_user_search()
    list_display = ['id', 'user', 'position', 'getSchool']
admin_site.register(EducatorInfo, EducatorInfoAdmin)

class K12SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'grades', 'contact_title', 'contact_name', 'school_type']
    formfield_overrides = {
        models.TextField: {'widget': forms.TextInput(attrs={'size':'50',}),},
    }
    search_fields = ['name', 'contact__first_name', 'contact__last_name'] #no, using default_user_search does not work.
    list_filter = ['school_type']
    def contact_name(self, obj):
        if obj.contact:
            return "%s %s" % (obj.contact.first_name, obj.contact.last_name)
        return None
    contact_name.short_description = 'Contact name'

admin_site.register(K12School, K12SchoolAdmin)

class GradeChangeRequestAdmin(admin.ModelAdmin):
    list_display = ['requesting_student', 'claimed_grade', 'approved','acknowledged_by','acknowledged_time', 'created']
    readonly_fields = ['grade_before_request', 'requesting_student','acknowledged_by','acknowledged_time','claimed_grade']
    search_fields = default_user_search('requesting_student')
    list_filter = ('created','approved',)

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'acknowledged_by', None) is None:
            obj.acknowledged_by = request.user
        if getattr(obj, 'acknowledged_time', None) is None and getattr(request.POST, 'approved', None) is True:
            obj.acknowledged_time = datetime.datetime.now()
        obj.save()
admin_site.register(GradeChangeRequest, GradeChangeRequestAdmin)

#   Include admin pages for Django group
admin_site.register(Group, GroupAdmin)

