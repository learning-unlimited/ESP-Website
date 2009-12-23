from django.contrib import admin
from esp.users.models.userbits import UserBit, UserBitImplication
from esp.users.models import ContactInfo, StudentInfo, TeacherInfo, GuardianInfo, EducatorInfo, ZipCode, ZipCodeSearches

class UserBitAdmin(admin.ModelAdmin):
    search_fields = ['user__last_name','user__first_name',
                     'qsc__uri','verb__uri']
admin.site.register(UserBit, UserBitAdmin)


class UserBitImplicationAdmin(admin.ModelAdmin):
    exclude = ('created_bits',)

admin.site.register(UserBitImplication, UserBitImplicationAdmin)

admin.site.register(ContactInfo)
admin.site.register(StudentInfo)
admin.site.register(TeacherInfo)
admin.site.register(GuardianInfo)
admin.site.register(EducatorInfo)
admin.site.register(ZipCode)
admin.site.register(ZipCodeSearches)
