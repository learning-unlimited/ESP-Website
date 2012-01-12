
""" Admin settings for esp.utils. """

from esp.utils.models import TemplateOverride

from django.contrib import admin
from esp.admin import admin_site
from reversion.admin import VersionAdmin


class TemplateOverrideAdmin(VersionAdmin):
    exclude = ['version']
    search_fields = ['name']
    list_display = ['id', 'name', 'version', ]
    list_display_links = ['id', 'name', ]

admin_site.register(TemplateOverride, TemplateOverrideAdmin)
