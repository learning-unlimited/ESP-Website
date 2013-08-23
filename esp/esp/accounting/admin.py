__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@lists.learningu.org
"""
from django.contrib import admin
from esp.admin import admin_site
from esp.accounting.models import Transfer, Account, FinancialAidGrant, LineItemType, LineItemOptions

class LIOInline(admin.TabularInline):
    model = LineItemOptions

class LITAdmin(admin.ModelAdmin):
    list_display = ['text', 'amount', 'program', 'required', 'num_options', 'max_quantity']
    search_fields = ['text', 'amount', 'program__url']
    inlines = [LIOInline,]
admin_site.register(LineItemType, LITAdmin)

class TransferAdmin(admin.ModelAdmin):
    list_display = ['id', 'line_item', 'user', 'timestamp', 'source', 'destination', 'amount_dec', 'executed']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'source__name', 'destination__name', 'line_item__text']
admin_site.register(Transfer, TransferAdmin)

class AccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'program', 'balance']
admin_site.register(Account, AccountAdmin)

def finalize_finaid_grants(modeladmin, request, queryset):
    for grant in queryset:
        grant.finalize()
class FinancialAidGrantAdmin(admin.ModelAdmin):
    list_display = ['id', 'request', 'user', 'program', 'finalized', 'amount_max_dec', 'percent']
    actions = [ finalize_finaid_grants, ]
admin_site.register(FinancialAidGrant, FinancialAidGrantAdmin)


