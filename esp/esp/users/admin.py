from django.contrib import admin
from esp.admin import admin_site
from django import forms
from django.db import models
from esp.users.models.userbits import UserBit, UserBitImplication
from esp.users.models.forwarder import UserForwarder
from esp.users.models import UserAvailability, ContactInfo, StudentInfo, TeacherInfo, GuardianInfo, EducatorInfo, ZipCode, ZipCodeSearches, K12School, ESPUser, Record, Permission
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
import datetime

class UserBitAdmin(admin.ModelAdmin):
    list_display = [ 'id', 'user', 'qsc', 'verb', 'startdate', 'enddate', 'recursive', ]
    search_fields = ['user__last_name','user__first_name','user__username',
                     'qsc__uri','verb__uri']
    actions = [ 'expire', 'renew' ]

    def expire(self, request, queryset):
        rows_updated = queryset.update(enddate=datetime.datetime.now())
        if rows_updated == 1:
            message_bit = "1 userbit was"
        else:
            message_bit = "%s userbits were" % rows_updated
        self.message_user(request, "%s successfully expired." % message_bit)
    expire.short_description = "Expire bits"

    def renew(self, request, queryset):
        rows_updated = queryset.update(enddate=datetime.datetime(9999, 01, 01))
        if rows_updated == 1:
            message_bit = "1 userbit was"
        else:
            message_bit = "%s userbits were" % rows_updated
        self.message_user(request, "%s successfully expired." % message_bit)
    renew.short_description = "Renew bits"
    


class UserBitImplicationAdmin(admin.ModelAdmin):
    exclude = ('created_bits',)


admin_site.register(UserForwarder)

admin_site.register(ZipCode)
admin_site.register(ZipCodeSearches)
admin_site.register(UserAvailability)

class ESPUserAdmin(UserAdmin):
    #remove the user_permissions and is_superuser from adminpage
    #(since we don't use either of those)
    #See https://github.com/django/django/blob/stable/1.3.x/django/contrib/auth/admin.py

    from django.utils.translation import ugettext, ugettext_lazy as _
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff',)}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('User Roles'), {'fields': ('groups',)}),
        )

admin_site.register(ESPUser, ESPUserAdmin)

class RecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'event', 'program']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
admin_site.register(Record, RecordAdmin)

class PermissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'role', 'permission_type','program','startdate','enddate']
admin_site.register(Permission, PermissionAdmin)

class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'e_mail', 'phone_day', 'address_postal']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'user__username',  'e_mail']
admin_site.register(ContactInfo, ContactInfoAdmin)

class UserInfoAdmin(admin.ModelAdmin):
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'user__username',  'user__email']

class StudentInfoAdmin(UserInfoAdmin):
    list_display = ['id', 'user', 'graduation_year', 'k12school', 'school']
admin_site.register(StudentInfo, StudentInfoAdmin)

class TeacherInfoAdmin(UserInfoAdmin):
    list_display = ['id', 'user', 'graduation_year', 'from_here', 'college']
admin_site.register(TeacherInfo, TeacherInfoAdmin)

class GuardianInfoAdmin(UserInfoAdmin):
    list_display = ['id', 'user', 'year_finished', 'num_kids']
admin_site.register(GuardianInfo, GuardianInfoAdmin)

class EducatorInfoAdmin(UserInfoAdmin):
    list_display = ['id', 'user', 'position', 'k12school', 'school']
admin_site.register(EducatorInfo, EducatorInfoAdmin)


class K12SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'grades', 'contact_title', 'contact_name', 'school_type']
    formfield_overrides = {
        models.TextField: {'widget': forms.TextInput(attrs={'size':'50',}),},
    }

    def contact_name(self, obj):
        return "%s %s" % (obj.contact.first_name, obj.contact.last_name)
    contact_name.short_description = 'Contact name'

admin_site.register(K12School, K12SchoolAdmin)

#   Include admin pages for Django group
admin_site.register(Group, GroupAdmin)

