" Survey models for Educational Studies Program. "

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

from django.contrib import admin
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from esp.admin import admin_site
from esp.survey.models import Survey, SurveyResponse, QuestionType, Question, Answer
from esp.survey.forms import QuestionImportForm, DuplicateResolutionForm
from esp.survey.importers import CSVQuestionImporter, TemplateManager

class SurveyAdmin(admin.ModelAdmin):
    list_filter = ('category',)
    actions = ['import_questions', 'export_questions']
    
    def import_questions(self, request, queryset):
        """Multi-step import workflow: upload → validate → resolve duplicates → import."""
        
        # Step 1: Check if we have exactly one survey selected
        if queryset.count() != 1:
            self.message_user(
                request,
                'Please select exactly one survey for import.',
                level=messages.ERROR
            )
            return HttpResponseRedirect(request.get_full_path())
        
        target_survey = queryset.first()
        
        # Step 2: Handle form submission
        if request.method == 'POST':
            # Check which step we're on
            if 'resolve_duplicates' in request.POST:
                # Step 4: Process duplicate resolution
                return self._process_duplicate_resolution(request, target_survey)
            else:
                # Step 3: Process initial import form
                return self._process_import_form(request, target_survey)
        
        # Step 2: Display initial import form
        form = QuestionImportForm()
        context = {
            'form': form,
            'survey': target_survey,
            'opts': self.model._meta,
            'title': f'Import Questions into {target_survey.name}',
        }
        return render(request, 'admin/survey/import_questions.html', context)
    
    import_questions.short_description = "Import questions from CSV or template"
    
    def _process_import_form(self, request, target_survey):
        """Process the initial import form submission."""
        form = QuestionImportForm(request.POST, request.FILES)
        
        if not form.is_valid():
            # Display form with validation errors
            context = {
                'form': form,
                'survey': target_survey,
                'opts': self.model._meta,
                'title': f'Import Questions into {target_survey.name}',
            }
            return render(request, 'admin/survey/import_questions.html', context)
        
        # Get the import source
        import_source = form.cleaned_data['import_source']
        
        # Create importer based on source
        if import_source == 'upload':
            csv_file = form.cleaned_data['csv_file']
            importer = CSVQuestionImporter(csv_file, target_survey)
        else:  # template
            template_name = form.cleaned_data['template']
            try:
                importer = TemplateManager.load_template(template_name, target_survey)
            except FileNotFoundError as e:
                messages.error(request, str(e))
                context = {
                    'form': form,
                    'survey': target_survey,
                    'opts': self.model._meta,
                    'title': f'Import Questions into {target_survey.name}',
                }
                return render(request, 'admin/survey/import_questions.html', context)
        
        # Validate the CSV
        validation_result = importer.validate()
        
        if not validation_result['is_valid']:
            # Display validation errors
            error_messages = [
                f"Row {err.row_number}, {err.field}: {err.message}"
                for err in validation_result['errors']
            ]
            for error_msg in error_messages:
                messages.error(request, error_msg)
            
            context = {
                'form': form,
                'survey': target_survey,
                'opts': self.model._meta,
                'title': f'Import Questions into {target_survey.name}',
            }
            return render(request, 'admin/survey/import_questions.html', context)
        
        # Check for duplicates
        questions = importer.parse_questions()
        duplicates = importer.validator.check_duplicates(questions, target_survey)
        
        if duplicates:
            # Display duplicate resolution form
            duplicate_form = DuplicateResolutionForm(duplicates)
            
            # Store importer data in session for next step
            # We'll store the CSV content and import source
            if import_source == 'upload':
                csv_content = csv_file.read().decode('utf-8')
                request.session['import_csv_content'] = csv_content
                request.session['import_source'] = 'upload'
            else:
                request.session['import_template_name'] = template_name
                request.session['import_source'] = 'template'
            
            request.session['import_survey_id'] = target_survey.id
            
            context = {
                'form': duplicate_form,
                'duplicates': duplicates,
                'survey': target_survey,
                'opts': self.model._meta,
                'title': f'Resolve Duplicate Questions - {target_survey.name}',
            }
            return render(request, 'admin/survey/resolve_duplicates.html', context)
        
        # No duplicates, proceed with import
        result = importer.import_questions()
        
        if result.success:
            messages.success(
                request,
                f'Successfully imported {result.created_count} questions into {target_survey.name}'
            )
        else:
            for error in result.errors:
                messages.error(request, error)
        
        # Redirect back to survey list
        return HttpResponseRedirect(reverse('admin:survey_survey_changelist'))
    
    def _process_duplicate_resolution(self, request, target_survey):
        """Process the duplicate resolution form submission."""
        
        # Retrieve importer data from session
        import_source = request.session.get('import_source')
        survey_id = request.session.get('import_survey_id')
        
        if not import_source or survey_id != target_survey.id:
            messages.error(request, 'Session expired. Please try importing again.')
            return HttpResponseRedirect(reverse('admin:survey_survey_changelist'))
        
        # Recreate the importer
        if import_source == 'upload':
            csv_content = request.session.get('import_csv_content')
            if not csv_content:
                messages.error(request, 'Session expired. Please try importing again.')
                return HttpResponseRedirect(reverse('admin:survey_survey_changelist'))
            importer = CSVQuestionImporter(csv_content, target_survey)
        else:  # template
            template_name = request.session.get('import_template_name')
            if not template_name:
                messages.error(request, 'Session expired. Please try importing again.')
                return HttpResponseRedirect(reverse('admin:survey_survey_changelist'))
            try:
                importer = TemplateManager.load_template(template_name, target_survey)
            except FileNotFoundError as e:
                messages.error(request, str(e))
                return HttpResponseRedirect(reverse('admin:survey_survey_changelist'))
        
        # Parse questions and check duplicates again
        questions = importer.parse_questions()
        duplicates = importer.validator.check_duplicates(questions, target_survey)
        
        # Process the duplicate resolution form
        duplicate_form = DuplicateResolutionForm(duplicates, request.POST)
        
        if not duplicate_form.is_valid():
            # Display form with validation errors
            context = {
                'form': duplicate_form,
                'duplicates': duplicates,
                'survey': target_survey,
                'opts': self.model._meta,
                'title': f'Resolve Duplicate Questions - {target_survey.name}',
            }
            return render(request, 'admin/survey/resolve_duplicates.html', context)
        
        # Get the selected strategies
        duplicate_strategy = duplicate_form.get_strategies(duplicates)
        
        # Perform the import with duplicate strategies
        result = importer.import_questions(duplicate_strategy)
        
        # Clean up session data
        request.session.pop('import_csv_content', None)
        request.session.pop('import_template_name', None)
        request.session.pop('import_source', None)
        request.session.pop('import_survey_id', None)
        
        if result.success:
            # Build success message with counts
            message_parts = []
            if result.created_count > 0:
                message_parts.append(f'{result.created_count} created')
            if result.updated_count > 0:
                message_parts.append(f'{result.updated_count} updated')
            if result.skipped_count > 0:
                message_parts.append(f'{result.skipped_count} skipped')
            
            message = f"Successfully imported questions into {target_survey.name}: {', '.join(message_parts)}"
            messages.success(request, message)
        else:
            for error in result.errors:
                messages.error(request, error)
        
        # Redirect back to survey list
        return HttpResponseRedirect(reverse('admin:survey_survey_changelist'))
    
    def export_questions(self, request, queryset):
        """Export questions from selected survey to CSV file."""
        
        # Check if we have exactly one survey selected
        if queryset.count() != 1:
            self.message_user(
                request,
                'Please select exactly one survey for export.',
                level=messages.ERROR
            )
            return HttpResponseRedirect(request.get_full_path())
        
        target_survey = queryset.first()
        
        # Generate CSV using CSVQuestionImporter.export_questions
        csv_content = CSVQuestionImporter.export_questions(target_survey)
        
        # Create HTTP response with CSV content
        response = HttpResponse(csv_content, content_type='text/csv')
        
        # Set filename for download
        filename = f'{target_survey.name}_questions.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    export_questions.short_description = "Export questions to CSV file"

admin_site.register(Survey, SurveyAdmin)

class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ('survey', 'time_filled')
    date_hierarchy = 'time_filled'
    list_filter = ('survey', 'time_filled')
admin_site.register(SurveyResponse, SurveyResponseAdmin)

class QuestionTypeAdmin(admin.ModelAdmin):
    list_display = ('name', '_param_names', 'is_numeric', 'is_countable')
admin_site.register(QuestionType, QuestionTypeAdmin)

class QuestionAdmin(admin.ModelAdmin):
    list_display = ['seq', 'name', 'question_type', 'survey', 'per_class']
    list_display_links = ['name']
    list_filter = ['survey']
    search_filter = ('name',)
admin_site.register(Question, QuestionAdmin)

admin_site.register(Answer)
