
""" Admin settings for esp.utils. """

from __future__ import absolute_import
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
    """ Day-of print locations. Connect, disconnect and change printers on the
    Printer Setup page (/manage/printers/), which keeps their state consistent. """
    list_display = ['name', 'is_default', 'mode', 'network_address', 'archived', 'trouble', 'last_result',
                    'last_result_at']
    list_filter = ['mode', 'archived']
    search_fields = ['name', 'network_address']
    readonly_fields = ['queue_id', 'laptop_token', 'laptop_last_seen', 'last_result', 'last_result_at', 'last_error',
                       'last_ok_at', 'trouble', 'trouble_since']


class PrintRequestAdmin(admin.ModelAdmin):
    """ Every day-of print job: what, where, who, and how it went. """
    list_display = ['id', 'description', 'kind', 'status', 'printer', 'pages', 'copies', 'requested_by',
                    'time_requested', 'time_executed', 'short_error']
    list_display_links = ['id', 'description']
    list_filter = ['status', 'kind', 'printer', 'program', 'time_requested']
    list_select_related = ['printer', 'user', 'receipt', 'requested_by']
    date_hierarchy = 'time_requested'
    ordering = ['-id']
    search_fields = default_user_search() + default_user_search('requested_by') + ['title', 'server_job']
    #   What the print worker and laptops keep up to date
    readonly_fields = ['server_job', 'attempts', 'refusals', 'refused_at', 'pages', 'time_requested',
                       'time_executed', 'document_json', 'deposit_slip']

    def description(self, job):
        return job.describe()
    description.short_description = 'What'

    def short_error(self, job):
        return job.error[:80] + ('...' if len(job.error) > 80 else '')
    short_error.short_description = 'Error'

admin_site.register(TemplateOverride, TemplateOverrideAdmin)
admin_site.register(Printer, PrinterAdmin)
admin_site.register(PrintRequest, PrintRequestAdmin)
