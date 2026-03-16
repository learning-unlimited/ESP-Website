" Survey import/export forms for Educational Studies Program. "

__author__    = "$LastChangedBy$"
__date__      = "$LastChangedDate$"
__rev__       = "$LastChangedRevision$"
__headurl__   = "$HeadURL$"
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

from django import forms
from esp.survey.importers import TemplateManager


class QuestionImportForm(forms.Form):
    """Form for selecting import source (CSV upload or template)."""
    
    IMPORT_SOURCE_CHOICES = [
        ('upload', 'Upload CSV'),
        ('template', 'Use Template')
    ]
    
    import_source = forms.ChoiceField(
        choices=IMPORT_SOURCE_CHOICES,
        label='Import Source',
        help_text='Choose whether to upload a CSV file or use a predefined template'
    )
    
    csv_file = forms.FileField(
        required=False,
        label='CSV File',
        help_text='Upload a CSV file containing survey questions'
    )
    
    template = forms.ChoiceField(
        required=False,
        label='Template',
        help_text='Select a predefined question template'
    )
    
    def __init__(self, *args, **kwargs):
        super(QuestionImportForm, self).__init__(*args, **kwargs)
        
        # Populate template choices from TemplateManager
        templates = TemplateManager.list_templates()
        template_choices = [('', '--- Select a template ---')]
        template_choices.extend([(t, t) for t in templates])
        self.fields['template'].choices = template_choices
    
    def clean(self):
        """Validate that exactly one source is provided based on import_source value."""
        cleaned_data = super(QuestionImportForm, self).clean()
        import_source = cleaned_data.get('import_source')
        csv_file = cleaned_data.get('csv_file')
        template = cleaned_data.get('template')
        
        if import_source == 'upload':
            if not csv_file:
                raise forms.ValidationError(
                    'Please upload a CSV file when using the upload option.'
                )
        elif import_source == 'template':
            if not template:
                raise forms.ValidationError(
                    'Please select a template when using the template option.'
                )
        
        return cleaned_data


class DuplicateResolutionForm(forms.Form):
    """Form for resolving duplicate questions during import."""
    
    RESOLUTION_CHOICES = [
        ('skip', 'Skip'),
        ('replace', 'Replace'),
        ('rename', 'Rename')
    ]
    
    def __init__(self, duplicates, *args, **kwargs):
        """Initialize form with dynamic fields for each duplicate.
        
        Args:
            duplicates: List of Duplicate objects from importers.py
        """
        super(DuplicateResolutionForm, self).__init__(*args, **kwargs)
        
        # Create a field for each duplicate
        for duplicate in duplicates:
            existing_question = duplicate.existing_question
            question_data = duplicate.question_data
            
            # Field name format: duplicate_{question_id}
            field_name = f'duplicate_{existing_question.id}'
            
            # Label showing question name and type
            label = f'{question_data.question_name} ({question_data.question_type_name})'
            
            # Create ChoiceField with resolution options
            self.fields[field_name] = forms.ChoiceField(
                choices=self.RESOLUTION_CHOICES,
                label=label,
                initial='skip',
                help_text=f'Choose how to handle this duplicate question'
            )
    
    def get_strategies(self, duplicates):
        """Return a dictionary mapping question keys to selected strategies.
        
        Args:
            duplicates: List of Duplicate objects used to initialize the form
            
        Returns:
            Dict mapping "{question_name}|{question_type_name}" to strategy
        """
        strategies = {}
        
        for duplicate in duplicates:
            existing_question = duplicate.existing_question
            question_data = duplicate.question_data
            
            # Get the selected strategy from the form data
            field_name = f'duplicate_{existing_question.id}'
            strategy = self.cleaned_data.get(field_name, 'skip')
            
            # Create key matching the format used in CSVQuestionImporter
            key = f"{question_data.question_name}|{question_data.question_type_name}"
            strategies[key] = strategy
        
        return strategies
