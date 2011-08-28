from django.contrib import admin

from esp.customforms.models import Form, Page, Section, Field, Attribute


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


""" Classes to control display of instances on admin site """

class FormAdmin(admin.ModelAdmin):
    list_display = ['title', 'date_created', 'created_by', num_fields]
admin.site.register(Form, FormAdmin)

class PageAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'form', 'seq', num_sections]
admin.site.register(Page, PageAdmin)

class SectionAdmin(admin.ModelAdmin):
    list_display = ['title', page_form, 'page', 'seq', num_fields]
admin.site.register(Section, SectionAdmin)

class FieldAdmin(admin.ModelAdmin):
    list_display = ['__unicode__', 'form', 'label', 'field_type', 'section', 'seq', 'required']
    list_editable = list_display[2:]
admin.site.register(Field, FieldAdmin)

class AttributeAdmin(admin.ModelAdmin):
    list_display = ['attr_type', 'field', 'value']
    list_editable = ['value']
admin.site.register(Attribute, AttributeAdmin)


