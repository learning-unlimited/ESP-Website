from django import forms
from django.core import validators
import re
from esp.datatree.models import DataTree
from esp.program.models import ClassCategories, Class
from esp.program.manipulators import isValidSATSectionScore

class OnSiteRegManipulator(forms.Manipulator):
    def __init__(self):
        self.fields = (
            forms.TextField(field_name="first_name", \
                            length=20, \
                            maxlength=64, \
                            is_required=True, \
                            validator_list=[validators.isNotEmpty]),
            forms.TextField(field_name="last_name", \
                            length=30, \
                            maxlength=64, \
                            is_required=True, \
                            validator_list=[validators.isNotEmpty]),
            forms.EmailField(field_name="email", \
                            length=20, \
                            maxlength=64, \
                            is_required=True, \
                            validator_list=[validators.isNotEmpty]),
            forms.PositiveIntegerField(field_name="old_math_score", length=3, maxlength=3, validator_list=[isValidSATSectionScore]),
            forms.PositiveIntegerField(field_name="old_verb_score", length=3, maxlength=3, validator_list=[isValidSATSectionScore]),
            forms.PositiveIntegerField(field_name="old_writ_score", length=3, maxlength=3, validator_list=[isValidSATSectionScore]),
            forms.CheckboxField(field_name="paid"),
            forms.CheckboxField(field_name="medical"),
            forms.CheckboxField(field_name="liability")
            
            )
        
            
            
            
class TeacherClassRegManipulator(forms.Manipulator):
    """Manipulator for A class registration """
    def __init__(self, module):
        
        class_sizes = module.getClassSizes()
        class_sizes = zip(class_sizes, class_sizes)
        size_order = IsLessThanOtherField('class_size_max', 'Minimum size must be less than the maximum size.')
        
        class_grades = module.getClassGrades()
        class_grades = zip(class_grades, class_grades)

        grade_order = IsLessThanOtherField('grade_max', 'Minimum grade must be less than the maximum grade.')
        

        categories = ClassCategories.objects.all().order_by('category')
        categories = [ (x.id, x.category) for x in categories ]

        self.fields = (
            forms.TextField(field_name="title", \
                            length=50, \
                            maxlength=64, \
                            is_required=True, \
                            validator_list=[validators.isNotEmpty]),

            forms.LargeTextField(field_name="class_info", \
                            is_required=True, \
                            validator_list=[validators.isNotEmpty]),
            
            forms.SelectField(field_name="category", \
                              is_required=True, \
                              choices=categories),

            forms.SelectField(field_name="grade_min", \
                              is_required=True, \
                              choices=class_grades, \
                              validator_list=[grade_order]),
            
            forms.SelectField(field_name="grade_max", \
                              is_required=True, \
                              choices=class_grades),
            
            forms.SelectField(field_name="class_size_min", \
                              is_required=True, \
                              choices=class_sizes, \
                              validator_list=[size_order]),

            forms.SelectField(field_name="class_size_max", \
                              is_required=True, \
                              choices=class_sizes),

            CheckboxSelectMultipleField(field_name="resources", \
                                              choices=module.getResources()),

            forms.LargeTextField(field_name="message_for_directors", \
                                 is_required=False)

            )

        if module.classRegInfo.display_times:
            if module.classRegInfo.times_selectmultiple:
                self.fields = self.fields + (CheckboxSelectMultipleField(field_name="viable_times", \
                                             choices=module.getTimes()),)
            else:
                self.fields = self.fields + (forms.SelectField(field_name="viable_times", \
                                              choices=module.getTimes()),)

        if not module.classRegInfo.display_times or module.classRegInfo.times_selectmultiple:
            self.fields = self.fields + (forms.SelectField(field_name="duration", \
                                                           choices=module.getDurations()),)


class IsLessThanOtherField(object):
    def __init__(self, other_field_name, error_message):
        self.other, self.error_message = other_field_name, error_message

    def __call__(self, field_data, all_data):
        if float(field_data) > float(all_data[self.other]):
            raise validators.ValidationError, self.error_message


class isClassSlugUnique(object):
    def __init__(self, program):
        self.program = program

    def __call__(self, field_data, all_data):
        class_anchors = DataTree.objects.filter(parent = self.program.classes_node(),
                                          name   = field_data)
        if len(class_anchors) < 1:
            return

        classes = Class.objects.filter(anchor = class_anchors[0])
        if len(classes) < 1:
            return

        if str(classes[0].id) != all_data['class_id']:
            raise validators.ValidationError, 'Please choose a unique slug, "%s" chosen already.' % field_data
        
    

# Django's CheckboxSelectMultipleField fails miserably, and It's probably very version-dependent.
# Here's an ESP implementation that'll work on (many) django platforms
class CheckboxSelectMultipleField(forms.SelectMultipleField):
    """
    This has an identical interface to SelectMultipleField, except the rendered
    widget is different. Instead of a <select multiple>, this widget outputs a
    <ul> of <input type="checkbox">es.

    Of course, that results in multiple form elements for the same "single"
    field, so this class's prepare() method flattens the split data elements
    back into the single list that validators, renderers and save() expect.
    """
    requires_data_list = True
    def __init__(self, field_name, choices=None, ul_class='', validator_list=None):
        if validator_list is None: validator_list = []
        if choices is None: choices = []
        self.ul_class = ul_class
        forms.SelectMultipleField.__init__(self, field_name, choices, size=1, is_required=False, validator_list=validator_list)

    def prepare(self, new_data):
        # new_data has "split" this field into several fields, so flatten it
        # back into a single list.
        data_list = []
        for value, readable_value in self.choices:
            if new_data.get('%s%s' % (self.field_name, value), '') == 'on':
                data_list.append(value)
        new_data.setlist(self.field_name, data_list)
        assert False, self.field_name

    def render(self, data):
        output = ['<ul%s>' % (self.ul_class and ' class="%s"' % self.ul_class or '')]
        str_data_list = map(str, data) # normalize to strings
        for value, choice in self.choices:
            checked_html = ''
            if str(value) in str_data_list:
                checked_html = ' checked="checked"'
            field_name = '%s%s' % (self.field_name, value)
            output.append('<li><input type="checkbox" id="%s" class="v%s" name="%s" value="%s"%s /> <label for="%s">%s</label></li>' % \
                (self.get_id() + value, self.__class__.__name__, self.field_name, value, checked_html,
                self.get_id() + value, choice))
        output.append('</ul>')
        return '\n'.join(output)

