
""" Admin settings for esp.utils. """

from esp.utils.models import TemplateOverride

from django.contrib import admin

class TemplateOverrideAdmin(admin.ModelAdmin):
    exclude = ['version']
    search_fields = ['name']

admin.site.register(TemplateOverride, TemplateOverrideAdmin)
