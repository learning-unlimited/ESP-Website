from esp.tagdict.models import Tag
from django.contrib import admin

class TagAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'target', )

admin.site.register(Tag, TagAdmin)
