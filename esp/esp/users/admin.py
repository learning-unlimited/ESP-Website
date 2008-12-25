from django.contrib import admin
from esp.users.models.userbits import UserBit, UserBitImplication
from esp.users.models import ContactInfo, StudentInfo, TeacherInfo, GuardianInfo, EducatorInfo

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
