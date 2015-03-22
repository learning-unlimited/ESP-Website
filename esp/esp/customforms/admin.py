from django.contrib import admin
from esp.admin import admin_site

from esp.customforms.models import Form, Page, Section, Field, Attribute
from esp.utils.admin_user_search import default_user_search

""" Functions to fetch data for columns """

def num_fields(obj):
    return obj.field_set.all().count()
num_fields.short_description = 'Number of fields'

def num_sections(obj):
    return obj.section_set.all().count()
num_sections.short_description = 'Number of sections'

def page_form(obj):
    return obj.page.form
page_form.short_description = 'Form'

def field_form(obj):
    return obj.field.form
field_form.short_description = 'Form'

""" Classes to control display of instances on admin site """

class FormAdmin(admin.ModelAdmin):
    list_display = ['title', 'date_created', 'created_by', num_fields]
    search_fields = default_user_search('created_by') + ['title', 'description']
    date_hierarchy = 'date_created'
admin_site.register(Form, FormAdmin)

class PageAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'form', 'seq', num_sections]
    list_filter = ('form',)
admin_site.register(Page, PageAdmin)

class SectionAdmin(admin.ModelAdmin):
    list_display = ['title', page_form, 'page', 'seq', num_fields]
    search_fields = ('title', 'description')
    list_filter = ('page', 'page__form')
admin_site.register(Section, SectionAdmin)

class FieldAdmin(admin.ModelAdmin):
    list_filter = ('form',)
    search_fields = ('label',)
    list_display = ['__unicode__', 'form', 'label', 'field_type', 'section', 'seq', 'required']
    list_editable = list_display[2:]
admin_site.register(Field, FieldAdmin)

class AttributeAdmin(admin.ModelAdmin):
    list_display = ['attr_type', 'field', 'value', field_form]
    list_filter = ('attr_type', 'field__form')
    list_editable = ['value']
    search_fields = ('field__label',)
admin_site.register(Attribute, AttributeAdmin)


