"""

Custom Teacher Registration Fields Model

This module provides database-driven custom field support for teacher registration,
allowing chapter administrators to add custom fields without requiring developer
support or hardcoded Python changes.

Author: ESP Web Team
"""

from django.db import models
from django import forms
from esp.program.models import Program
from esp.users.models import ESPUser


class TeacherRegistrationCustomField(models.Model):
    """
    A custom field that can be added to the teacher registration form.
    This allows chapter administrators to customize the class registration
    form without requiring hardcoded Python changes.
    """
    
    FIELD_TYPES = [
        ('text', 'Text Input'),
        ('textarea', 'Text Area'),
        ('integer', 'Integer'),
        ('float', 'Decimal Number'),
        ('boolean', 'Checkbox (True/False)'),
        ('select', 'Dropdown Select'),
        ('multiselect', 'Multiple Select'),
        ('radio', 'Radio Buttons'),
        ('email', 'Email Address'),
        ('url', 'URL'),
    ]
    
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='teacher_custom_fields')
    field_name = models.CharField(max_length=100, help_text='Unique identifier for this field (e.g., "qualifications")')
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES, default='text')
    label = models.CharField(max_length=200, help_text='Display label for the field')
    help_text = models.TextField(blank=True, help_text='Help text shown below the field')
    required = models.BooleanField(default=False, help_text='Whether this field is required')
    position = models.IntegerField(default=0, help_text='Display order (lower numbers appear first)')
    
    # Options for choice-based fields (select, multiselect, radio)
    choices = models.TextField(blank=True, help_text='Comma-separated choices for dropdown/radio fields')
    
    # Validation options
    max_length = models.IntegerField(null=True, blank=True, help_text='Maximum character length for text fields')
    min_value = models.FloatField(null=True, blank=True, help_text='Minimum value for number fields')
    max_value = models.FloatField(null=True, blank=True, help_text='Maximum value for number fields')
    
    # Visibility control
    is_visible = models.BooleanField(default=True, help_text='Whether this field is shown on the form')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(ESPUser, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['position', 'label']
        unique_together = [['program', 'field_name']]
        verbose_name = 'Teacher Registration Custom Field'
        verbose_name_plural = 'Teacher Registration Custom Fields'
    
    def __str__(self):
        return f"{self.label} ({self.field_name})"
    
    def get_choices_list(self):
        """Return choices as a list of tuples for form fields."""
        if not self.choices:
            return []
        return [(choice.strip(), choice.strip()) for choice in self.choices.split(',') if choice.strip()]
    
    def to_form_field(self):
        """Convert this model to a Django form field."""
        field_kwargs = {
            'label': self.label,
            'help_text': self.help_text,
            'required': self.required,
        }
        
        if self.field_type == 'text':
            if self.max_length:
                field_kwargs['max_length'] = self.max_length
            return forms.CharField(**field_kwargs)
        
        elif self.field_type == 'textarea':
            return forms.CharField(widget=forms.Textarea(), **field_kwargs)
        
        elif self.field_type == 'integer':
            field_kwargs['min_value'] = self.min_value
            field_kwargs['max_value'] = self.max_value
            return forms.IntegerField(**field_kwargs)
        
        elif self.field_type == 'float':
            field_kwargs['min_value'] = self.min_value
            field_kwargs['max_value'] = self.max_value
            return forms.FloatField(**field_kwargs)
        
        elif self.field_type == 'boolean':
            return forms.BooleanField(**field_kwargs)
        
        elif self.field_type in ('select', 'multiselect', 'radio'):
            choices = self.get_choices_list()
            if self.field_type == 'multiselect':
                field_kwargs['widget'] = forms.CheckboxSelectMultiple(choices=choices)
                return forms.MultipleChoiceField(choices=choices, **field_kwargs)
            elif self.field_type == 'radio':
                field_kwargs['widget'] = forms.RadioSelect(choices=choices)
                return forms.ChoiceField(choices=choices, **field_kwargs)
            else:  # select
                choices = [('', '-- Select --')] + choices
                return forms.ChoiceField(choices=choices, **field_kwargs)
        
        elif self.field_type == 'email':
            return forms.EmailField(**field_kwargs)
        
        elif self.field_type == 'url':
            return forms.URLField(**field_kwargs)
        
        # Default to text field
        return forms.CharField(**field_kwargs)


class TeacherRegistrationCustomFieldValue(models.Model):
    """
    Stores the value of a custom field for a specific class/teacher registration.
    """
    field = models.ForeignKey(TeacherRegistrationCustomField, on_delete=models.CASCADE, related_name='values')
    class_subject_id = models.IntegerField(help_text='ID of the ClassSubject')
    value = models.TextField(blank=True, help_text='The value submitted for this field')
    
    class Meta:
        verbose_name = 'Teacher Registration Custom Field Value'
        verbose_name_plural = 'Teacher Registration Custom Field Values'
        unique_together = [['field', 'class_subject_id']]
    
    def __str__(self):
        return f"{self.field.field_name}: {self.value}"
    
    def get_display_value(self):
        """Return the value in a human-readable format."""
        if self.field.field_type == 'boolean':
            return 'Yes' if self.value == 'true' or self.value == 'True' else 'No'
        
        # For choice fields, try to show the label instead of the value
        if self.field.field_type in ('select', 'multiselect', 'radio'):
            choices_dict = dict(self.field.get_choices_list())
            if self.field.field_type == 'multiselect':
                # Handle comma-separated values
                values = [v.strip() for v in self.value.split(',')]
                return ', '.join(choices_dict.get(v, v) for v in values)
            return choices_dict.get(self.value, self.value)
        
        return self.value
