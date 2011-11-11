
""" Admin settings for esp.utils. """

from esp.utils.models import TemplateOverride

from django.contrib import admin
from reversion.admin import VersionAdmin


class TemplateOverrideAdmin(VersionAdmin):
    exclude = ['version']
    search_fields = ['name']

admin.site.register(TemplateOverride, TemplateOverrideAdmin)
