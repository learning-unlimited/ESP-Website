from esp.tagdict.models import Tag
from django.contrib import admin
from esp.admin import admin_site

class TagAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'target', )
admin_site.register(Tag, TagAdmin)
