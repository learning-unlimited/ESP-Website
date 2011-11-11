
""" Admin settings for esp.utils. """

from esp.utils.models import TemplateOverride

from django.contrib import admin
from reversion.admin import VersionAdmin


class TemplateOverrideAdmin(VersionAdmin):
    exclude = ['version']
    search_fields = ['name']
    list_display = ['id', 'name', 'version', ]
    list_display_links = ['id', 'name', ]

admin.site.register(TemplateOverride, TemplateOverrideAdmin)
