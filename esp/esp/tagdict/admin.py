from esp.tagdict.models import Tag
from django.contrib import admin
from esp.admin import admin_site
from django.utils.html import format_html
from django import forms


class TagAdmin(admin.ModelAdmin):
    list_display = ('key', 'short_value', 'target',)
    list_filter = ('key', 'object_id', 'content_type__model',)

    def short_value(self, obj):
        val = obj.value or ""
        short = val[:50] + "..." if len(val) > 50 else val

        return format_html(
            '<div style="max-width:300px; word-break:break-word;">{}</div>',
            short
        )

    short_value.short_description = "Value"

    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super().formfield_for_dbfield(db_field, **kwargs)

        if db_field.name == 'value':
            field.widget = forms.Textarea(attrs={
                'style': 'width:100%; max-width:600px; word-break:break-word;',
                'rows': 4
            })

        return field


admin_site.register(Tag, TagAdmin)