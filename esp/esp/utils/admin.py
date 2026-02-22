
""" Admin settings for esp.utils. """

from esp.utils.models import TemplateOverride, Printer, PrintRequest
from esp.utils.admin_user_search import default_user_search

from django.contrib import admin
from esp.admin import admin_site
from reversion.admin import VersionAdmin


class TemplateOverrideAdmin(VersionAdmin):
    exclude = ['version']
    search_fields = ['name']
    list_display = ['id', 'name', 'version', ]
    list_display_links = ['id', 'name', ]

class PrinterAdmin(admin.ModelAdmin):
    list_display = ['name', 'printer_type']

class PrintRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'printer', 'time_requested', 'time_executed']
    list_filter = ['printer', 'time_requested', 'time_executed']
    date_hierarchy = 'time_requested'
    search_fields = default_user_search()

admin_site.register(TemplateOverride, TemplateOverrideAdmin)
admin_site.register(Printer, PrinterAdmin)
admin_site.register(PrintRequest, PrintRequestAdmin)
