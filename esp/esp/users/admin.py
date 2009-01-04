from django.contrib import admin
from django import forms
from esp.users.models.userbits import UserBit, UserBitImplication
from esp.users.models import ContactInfo, StudentInfo, TeacherInfo, GuardianInfo, EducatorInfo, K12School

class UserBitAdmin(admin.ModelAdmin):
    search_fields = ['user__last_name','user__first_name',
                     'qsc__uri','verb__uri']
admin.site.register(UserBit, UserBitAdmin)

admin.site.register(UserBitImplication)

admin.site.register(ContactInfo)
admin.site.register(StudentInfo)
admin.site.register(TeacherInfo)
admin.site.register(GuardianInfo)
admin.site.register(EducatorInfo)

class K12SchoolAdmin(admin.ModelAdmin):
    list_display = ( 'name', 'grades', 'school_type' )
    # Override a special function to customize the form. This feels unholy...
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'contact':
            return super(K12SchoolAdmin,self).formfield_for_dbfield(db_field,**kwargs)
        kwargs['widget'] = forms.TextInput(attrs={'size':'50'})
        return db_field.formfield(**kwargs)

admin.site.register(K12School, K12SchoolAdmin)
