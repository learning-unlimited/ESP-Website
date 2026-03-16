
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
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

from esp.dbmail.models import MessageVars, EmailList, PlainRedirect, MessageRequest, TextOfEmail
from esp.utils.admin_user_search import default_user_search

class MessageVarsAdmin(admin.ModelAdmin):
    list_display = ('id', 'messagerequest','provider_name')
    list_filter = ('provider_name',)
    search_fields = ('messagerequest__subject',)
admin_site.register(MessageVars, MessageVarsAdmin)

class EmailListAdmin(admin.ModelAdmin):
    list_display = ('description', 'regex')
admin_site.register(EmailList, EmailListAdmin)

class PlainRedirectAdmin(admin.ModelAdmin):
    list_display = ('original', 'destination')
    search_fields = ('original', 'destination')
admin_site.register(PlainRedirect, PlainRedirectAdmin)

class MessageRequestAdmin(admin.ModelAdmin):
    list_display = ('subject', 'creator', 'sender', 'recipients', 'created_at', 'processed_by', 'processed', 'public')
    list_filter = ('processed', 'processed_by', 'public')
    search_fields = default_user_search('creator') + ['subject', 'sender']
    date_hierarchy = 'processed_by'
admin_site.register(MessageRequest, MessageRequestAdmin)

class TextOfEmailAdmin(admin.ModelAdmin):
    list_display = ('id', 'send_from', 'send_to', 'subject', 'sent')
    search_fields = ('=id', 'send_from', 'send_to', 'subject')
    date_hierarchy = 'sent'
    list_filter = ('send_from',)
admin_site.register(TextOfEmail, TextOfEmailAdmin)
