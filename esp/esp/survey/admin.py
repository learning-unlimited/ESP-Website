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
from esp.survey.importers import CSVQuestionImporter, TemplateManager, ImportLogger

class SurveyAdmin(admin.ModelAdmin):
    list_filter = ('category',)
    actions = ['import_questions', 'export_questions']
    
    def import_questions(self, request, queryset):
        """Multi-step import workflow: upload → validate → resolve duplicates → import."""
        
        # Step 1: Check if we have at least one survey selected
        if queryset.count() == 0:
            self.message_user(
                request,
                'Please select at least one survey for import.',
                level=messages.ERROR
            )
            return HttpResponseRedirect(request.get_full_path())
        
        # Store selected survey IDs for batch processing
        target_surveys = list(queryset)
        
        # Step 2: Handle form submission
        if request.method == 'POST':
            # Check which step we're on
            if 'resolve_duplicates' in request.POST:
                # Step 4: Process duplicate resolution
                return self._process_duplicate_resolution(request, target_surveys)
            else:
                # Step 3: Process initial import form
                return self._process_import_form(request, target_surveys)
        
        # Step 2: Display initial import form
        form = QuestionImportForm()
        
        # Determine title based on number of surveys
        if len(target_surveys) == 1:
            title = f'Import Questions into {target_surveys[0].name}'
        else:
            title = f'Import Questions into {len(target_surveys)} surveys'
        
        context = {
            'form': form,
            'surveys': target_surveys,
            'opts': self.model._meta,
            'title': title,
        }
        return render(request, 'admin/survey/import_questions.html', context)
    
    import_questions.short_description = "Import questions from CSV or template"
    
    def _process_import_form(self, request, target_surveys):
        """Process the initial import form submission."""
        form = QuestionImportForm(request.POST, request.FILES)
        
        if not form.is_valid():
            # Display form with validation errors
            if len(target_surveys) == 1:
                title = f'Import Questions into {target_surveys[0].name}'
            else:
                title = f'Import Questions into {len(target_surveys)} surveys'
            
            context = {
                'form': form,
                'surveys': target_surveys,
                'opts': self.model._meta,
                'title': title,
            }
            return render(request, 'admin/survey/import_questions.html', context)
        
        # Get the import source
        import_source = form.cleaned_data['import_source']
        
        # Initialize logger
        logger = ImportLogger()
        
        # Determine source description for logging
        if import_source == 'upload':
            source_description = 'CSV upload'
            csv_file = form.cleaned_data['csv_file']
            
            # Validate file upload
            # Check file size (limit to 10MB)
            max_size = 10 * 1024 * 1024  # 10MB in bytes
            if csv_file.size > max_size:
                messages.error(
                    request,
                    f'File size exceeds maximum allowed size of 10MB. Your file is {csv_file.size / (1024 * 1024):.2f}MB.'
                )
                if len(target_surveys) == 1:
                    title = f'Import Questions into {target_surveys[0].name}'
                else:
                    title = f'Import Questions into {len(target_surveys)} surveys'
                
                context = {
                    'form': form,
                    'surveys': target_surveys,
                    'opts': self.model._meta,
                    'title': title,
                }
                return render(request, 'admin/survey/import_questions.html', context)
            
            # Check file type
            if not csv_file.name.endswith('.csv'):
                messages.error(
                    request,
                    f'Invalid file type. Please upload a CSV file. Your file: {csv_file.name}'
                )
                if len(target_surveys) == 1:
                    title = f'Import Questions into {target_surveys[0].name}'
                else:
                    title = f'Import Questions into {len(target_surveys)} surveys'
                
                context = {
                    'form': form,
                    'surveys': target_surveys,
                    'opts': self.model._meta,
                    'title': title,
                }
                return render(request, 'admin/survey/import_questions.html', context)
            
            # Check if file is empty
            if csv_file.size == 0:
                messages.error(request, 'The uploaded file is empty. Please upload a valid CSV file.')
                if len(target_surveys) == 1:
                    title = f'Import Questions into {target_surveys[0].name}'
                else:
                    title = f'Import Questions into {len(target_surveys)} surveys'
                
                context = {
                    'form': form,
                    'surveys': target_surveys,
                    'opts': self.model._meta,
                    'title': title,
                }
                return render(request, 'admin/survey/import_questions.html', context)
        else:  # template
            source_description = f'Template: {form.cleaned_data["template"]}'
        
        # Log import session start
        logger.log_start(request.user, target_surveys, source_description)
        
        # For batch import, we'll validate using the first survey as a reference
        # The actual import will happen per survey with error isolation
        reference_survey = target_surveys[0]
        
        # Create importer based on source with error handling
        try:
            if import_source == 'upload':
                csv_file = form.cleaned_data['csv_file']
                importer = CSVQuestionImporter(csv_file, reference_survey)
            else:  # template
                template_name = form.cleaned_data['template']
                try:
                    importer = TemplateManager.load_template(template_name, reference_survey)
                    
                    # Show info message about template
                    template_questions = importer.parse_questions()
                    messages.info(
                        request,
                        f'Template "{template_name}" contains {len(template_questions)} question(s)'
                    )
                except FileNotFoundError as e:
                    # Log failure
                    logger.log_failure([str(e)])
                    
                    messages.error(request, str(e))
                    if len(target_surveys) == 1:
                        title = f'Import Questions into {target_surveys[0].name}'
                    else:
                        title = f'Import Questions into {len(target_surveys)} surveys'
                    
                    context = {
                        'form': form,
                        'surveys': target_surveys,
                        'opts': self.model._meta,
                        'title': title,
                    }
                    return render(request, 'admin/survey/import_questions.html', context)
        except Exception as e:
            # Handle any errors during importer creation
            logger.log_failure([f"Error creating importer: {str(e)}"])
            messages.error(request, f"Error processing file: {str(e)}")
            
            if len(target_surveys) == 1:
                title = f'Import Questions into {target_surveys[0].name}'
            else:
                title = f'Import Questions into {len(target_surveys)} surveys'
            
            context = {
                'form': form,
                'surveys': target_surveys,
                'opts': self.model._meta,
                'title': title,
            }
            return render(request, 'admin/survey/import_questions.html', context)
        
        # Validate the CSV
        validation_result = importer.validate()
        
        if not validation_result['is_valid']:
            # Log validation failure
            logger.log_failure(validation_result['errors'])
            
            # Display validation errors
            error_messages = [
                f"Row {err.row_number}, {err.field}: {err.message}"
                for err in validation_result['errors']
            ]
            for error_msg in error_messages:
                messages.error(request, error_msg)
            
            if len(target_surveys) == 1:
                title = f'Import Questions into {target_surveys[0].name}'
            else:
                title = f'Import Questions into {len(target_surveys)} surveys'
            
            context = {
                'form': form,
                'surveys': target_surveys,
                'opts': self.model._meta,
                'title': title,
            }
            return render(request, 'admin/survey/import_questions.html', context)
        
        # Check for duplicates in the reference survey
        # For batch imports, we'll handle duplicates per survey during import
        questions = importer.parse_questions()
        duplicates = importer.validator.check_duplicates(questions, reference_survey)
        
        if duplicates and len(target_surveys) == 1:
            # Only show duplicate resolution form for single survey imports
            # For batch imports, we'll skip duplicates automatically
            
            # Display warning message for duplicates
            messages.warning(
                request,
                f'Found {len(duplicates)} duplicate question(s) - please resolve conflicts'
            )
            
            duplicate_form = DuplicateResolutionForm(duplicates)
            
            # Store importer data in session for next step
            if import_source == 'upload':
                csv_content = csv_file.read().decode('utf-8')
                request.session['import_csv_content'] = csv_content
                request.session['import_source'] = 'upload'
            else:
                request.session['import_template_name'] = template_name
                request.session['import_source'] = 'template'
            
            request.session['import_survey_ids'] = [target_surveys[0].id]
            
            context = {
                'form': duplicate_form,
                'duplicates': duplicates,
                'survey': target_surveys[0],
                'opts': self.model._meta,
                'title': f'Resolve Duplicate Questions - {target_surveys[0].name}',
            }
            return render(request, 'admin/survey/resolve_duplicates.html', context)
        
        # No duplicates or batch import - proceed with import
        # For batch imports, import into each survey independently
        results = []
        total_created = 0
        total_updated = 0
        total_skipped = 0
        
        for target_survey in target_surveys:
            try:
                # Create a fresh importer for each survey
                if import_source == 'upload':
                    # Re-read the CSV content for each survey
                    csv_file.seek(0)
                    survey_importer = CSVQuestionImporter(csv_file, target_survey)
                else:
                    survey_importer = TemplateManager.load_template(template_name, target_survey)
                
                # For batch imports, automatically skip duplicates
                if len(target_surveys) > 1:
                    # Check for duplicates in this specific survey
                    survey_questions = survey_importer.parse_questions()
                    survey_duplicates = survey_importer.validator.check_duplicates(survey_questions, target_survey)
                    
                    # Build skip strategy for all duplicates
                    duplicate_strategy = {}
                    for dup in survey_duplicates:
                        duplicate_strategy[dup.existing_question.id] = 'skip'
                    
                    result = survey_importer.import_questions(duplicate_strategy)
                else:
                    result = survey_importer.import_questions()
                
                # Accumulate totals for logging
                if result.success:
                    total_created += result.created_count
                    total_updated += result.updated_count
                    total_skipped += result.skipped_count
                
                results.append({
                    'survey': target_survey,
                    'result': result,
                    'success': result.success
                })
            except Exception as e:
                # Catch any errors and continue with remaining surveys
                results.append({
                    'survey': target_survey,
                    'result': None,
                    'success': False,
                    'error': str(e)
                })
        
        # Log completion or failure
        success_count = sum(1 for r in results if r['success'])
        if success_count > 0:
            # Log successful completion with totals
            logger.log_complete(total_created, total_updated, total_skipped)
        
        # Log any failures
        failure_results = [r for r in results if not r['success']]
        if failure_results:
            failure_errors = []
            for result_data in failure_results:
                survey_name = result_data['survey'].name
                if result_data.get('error'):
                    failure_errors.append(f"{survey_name}: {result_data['error']}")
                elif result_data.get('result'):
                    for error in result_data['result'].errors:
                        failure_errors.append(f"{survey_name}: {error}")
            
            if failure_errors:
                logger.log_failure(failure_errors)
        
        # Display results
        failure_count = len(results) - success_count
        
        if len(target_surveys) == 1:
            # Single survey import
            result_data = results[0]
            if result_data['success']:
                result = result_data['result']
                message_parts = []
                if result.created_count > 0:
                    message_parts.append(f'{result.created_count} created')
                if result.updated_count > 0:
                    message_parts.append(f'{result.updated_count} updated')
                if result.skipped_count > 0:
                    message_parts.append(f'{result.skipped_count} skipped')
                
                messages.success(
                    request,
                    f'Successfully imported questions into {result_data["survey"].name}: {", ".join(message_parts)}'
                )
            else:
                if result_data.get('error'):
                    messages.error(request, f'Import failed: {result_data["error"]}')
                else:
                    for error in result_data['result'].errors:
                        messages.error(request, error)
        else:
            # Batch import results - Summary message
            messages.success(
                request,
                f'Batch import complete: {success_count} survey(s) succeeded, {failure_count} survey(s) failed'
            )
            
            # Add warning if any questions were skipped due to duplicates
            if total_skipped > 0:
                messages.warning(
                    request,
                    f'{total_skipped} duplicate question(s) were automatically skipped across all surveys'
                )
            
            # Show detailed results for each survey separately
            for result_data in results:
                if result_data['success']:
                    result = result_data['result']
                    message_parts = []
                    if result.created_count > 0:
                        message_parts.append(f'{result.created_count} created')
                    if result.updated_count > 0:
                        message_parts.append(f'{result.updated_count} updated')
                    if result.skipped_count > 0:
                        message_parts.append(f'{result.skipped_count} skipped')
                    
                    messages.success(
                        request,
                        f'✓ {result_data["survey"].name}: {", ".join(message_parts)}'
                    )
                else:
                    error_msg = result_data.get('error', 'Unknown error')
                    messages.error(
                        request,
                        f'✗ {result_data["survey"].name}: Import failed - {error_msg}'
                    )
        
        # Redirect back to survey list
        return HttpResponseRedirect(reverse('admin:survey_survey_changelist'))
    
    def _process_duplicate_resolution(self, request, target_surveys):
        """Process the duplicate resolution form submission."""
        
        # Retrieve importer data from session
        import_source = request.session.get('import_source')
        survey_ids = request.session.get('import_survey_ids')
        
        # This method is only called for single survey imports with duplicates
        if not import_source or not survey_ids or len(survey_ids) != 1:
            messages.error(request, 'Session expired. Please try importing again.')
            return HttpResponseRedirect(reverse('admin:survey_survey_changelist'))
        
        target_survey = target_surveys[0]
        
        if survey_ids[0] != target_survey.id:
            messages.error(request, 'Session expired. Please try importing again.')
            return HttpResponseRedirect(reverse('admin:survey_survey_changelist'))
        
        # Initialize logger
        logger = ImportLogger()
        
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
                # Log failure
                logger.log_failure([str(e)])
                
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
        request.session.pop('import_survey_ids', None)
        
        if result.success:
            # Log successful completion
            logger.log_complete(result.created_count, result.updated_count, result.skipped_count)
            
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
            # Log failure
            logger.log_failure(result.errors)
            
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
