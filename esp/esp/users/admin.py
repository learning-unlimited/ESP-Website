from django.contrib import admin
from esp.users.models.userbits import UserBit, UserBitImplication

class UserBitAdmin(admin.ModelAdmin):
    search_fields = ['user__last_name','user__first_name',
                     'qsc__uri','verb__uri']
admin.site.register(UserBit, UserBitAdmin)

admin.site.register(UserBitImplication)

