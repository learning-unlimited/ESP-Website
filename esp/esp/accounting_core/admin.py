__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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
  Email: web-team@learningu.org
"""
from django.contrib import admin
from esp.admin import admin_site
from esp.accounting_core.models import LineItemType, Transaction, LineItem

class LITAdmin(admin.ModelAdmin):
    list_display = ['text', 'amount', 'anchor']
    search_fields = ['text', 'amount', 'anchor__uri']

class TXNAdmin(admin.ModelAdmin):
    list_display = ['id', 'timestamp', 'text', 'complete', ]
    list_display_links = list_display
    search_fields = ['id', 'text', ]

def transaction_id(lineitem):
    return lineitem.transaction_id
transaction_id.admin_order_field = 'transaction__id'

class LIAdmin(admin.ModelAdmin):
    list_display = ['id', transaction_id, 'amount', 'anchor', 'user', 'text', ]
    search_fields = ['id', 'transaction__id', 'amount', 'user__first_name', 'user__last_name', 'user__username', 'text', 'anchor__uri', 'amount']
