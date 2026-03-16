" CSV parsing and validation logic for survey question import. "

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

from dataclasses import dataclass
from typing import List, Optional, Dict
import csv
import io

from django.db import models
from esp.survey.models import Question, QuestionType


@dataclass
class QuestionData:
    """Parsed question data from CSV."""
    row_number: int
    question_name: str
    question_type_name: str
    param_values: List[str]
    per_class: bool
    sequence: Optional[int]


@dataclass
class ValidationError:
    """Validation error details with row number and message."""
    row_number: int
    field: str
    message: str


@dataclass
class Duplicate:
    """Duplicate question information."""
    question_data: QuestionData
    existing_question: 'Question'  # Forward reference to avoid circular import


@dataclass
class ImportResult:
    """Result of import operation with counts and errors."""
    success: bool
    created_count: int
    updated_count: int
    skipped_count: int
    errors: List[str]


class CSVQuestionImporter:
    """Handles parsing and validation of CSV question data."""
    
    REQUIRED_COLUMNS = ['question_name', 'question_type']
    OPTIONAL_COLUMNS = ['param_values', 'per_class', 'sequence']
    
    def __init__(self, csv_file, target_survey):
        """Initialize with file handle and target survey.
        
        Args:
            csv_file: File-like object or string containing CSV data
            target_survey: Survey object to import questions into
        """
        self.csv_file = csv_file
        self.target_survey = target_survey
        self.validator = QuestionValidator()
    
    @classmethod
    def export_questions(cls, survey):
        """Export questions from a survey to CSV format.
        
        Args:
            survey: Survey object to export questions from
            
        Returns:
            String containing CSV data with all questions
        """
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=['question_name', 'question_type', 'param_values', 'per_class', 'sequence']
        )
        
        # Write header row
        writer.writeheader()
        
        # Query all questions ordered by sequence
        questions = Question.objects.filter(survey=survey).order_by('seq')
        
        # Write each question as a row
        for question in questions:
            # Format param_values as pipe-delimited string
            param_values_str = '|'.join(question.param_values)
            
            # Format per_class as true/false
            per_class_str = 'true' if question.per_class else 'false'
            
            writer.writerow({
                'question_name': question.name,
                'question_type': question.question_type.name,
                'param_values': param_values_str,
                'per_class': per_class_str,
                'sequence': question.seq
            })
        
        return output.getvalue()
        
    def validate(self) -> Dict:
        """Validate CSV structure and content without creating objects.
        
        Returns:
            Dict with 'is_valid' bool and 'errors' list of ValidationError objects
        """
        errors = []
        
        try:
            questions = self.parse_questions()
            
            # Validate each question
            for question_data in questions:
                row_errors = self.validator.validate_row(
                    question_data.row_number,
                    {
                        'question_name': question_data.question_name,
                        'question_type': question_data.question_type_name,
                        'param_values': question_data.param_values,
                        'per_class': question_data.per_class,
                        'sequence': question_data.sequence
                    }
                )
                errors.extend(row_errors)
                
        except Exception as e:
            errors.append(ValidationError(
                row_number=0,
                field='file',
                message=f'CSV parsing error: {str(e)}'
            ))
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def parse_questions(self) -> List[QuestionData]:
        """Parse CSV into structured question data.
        
        Returns:
            List of QuestionData objects
            
        Raises:
            ValueError: If required columns are missing or CSV is malformed
            UnicodeDecodeError: If file encoding is not supported
        """
        # Handle both file objects and strings
        if isinstance(self.csv_file, str):
            csv_content = io.StringIO(self.csv_file)
        else:
            # Read file content and decode with error handling
            try:
                content = self.csv_file.read()
                if isinstance(content, bytes):
                    # Try UTF-8 first, then fall back to other encodings
                    try:
                        content = content.decode('utf-8')
                    except UnicodeDecodeError:
                        # Try UTF-16
                        try:
                            content = content.decode('utf-16')
                        except UnicodeDecodeError:
                            # Try Latin-1 as last resort
                            try:
                                content = content.decode('latin-1')
                            except UnicodeDecodeError:
                                raise ValueError(
                                    "Unable to decode CSV file. Please ensure the file is encoded in UTF-8, UTF-16, or Latin-1."
                                )
                csv_content = io.StringIO(content)
                # Reset file pointer for potential re-reading
                if hasattr(self.csv_file, 'seek'):
                    self.csv_file.seek(0)
            except Exception as e:
                if isinstance(e, ValueError):
                    raise
                raise ValueError(f"Error reading CSV file: {str(e)}")
        
        # Parse CSV with error handling for malformed data
        try:
            reader = csv.DictReader(csv_content)
        except csv.Error as e:
            raise ValueError(f"Malformed CSV file: {str(e)}")
        
        # Validate required columns are present
        if not reader.fieldnames:
            raise ValueError("CSV file is empty or has no headers")
            
        missing_columns = [col for col in self.REQUIRED_COLUMNS 
                          if col not in reader.fieldnames]
        if missing_columns:
            raise ValueError(
                f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        questions = []
        try:
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
                # Parse param_values from pipe-delimited string
                param_values_str = row.get('param_values', '').strip()
                if param_values_str:
                    param_values = [v.strip() for v in param_values_str.split('|')]
                else:
                    param_values = []
                
                # Parse per_class boolean
                per_class_str = row.get('per_class', '').strip().lower()
                per_class = self._parse_boolean(per_class_str)
                
                # Parse sequence integer
                sequence_str = row.get('sequence', '').strip()
                sequence = None
                if sequence_str:
                    try:
                        sequence = int(sequence_str)
                    except ValueError:
                        # Let validator handle this error
                        sequence = sequence_str
                
                question_data = QuestionData(
                    row_number=row_num,
                    question_name=row.get('question_name', '').strip(),
                    question_type_name=row.get('question_type', '').strip(),
                    param_values=param_values,
                    per_class=per_class,
                    sequence=sequence
                )
                questions.append(question_data)
        except csv.Error as e:
            raise ValueError(f"Malformed CSV data at row {row_num}: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing CSV data: {str(e)}")
        
        return questions
    
    def _parse_boolean(self, value: str) -> bool:
        """Parse boolean value from string.
        
        Args:
            value: String value to parse (true/false/1/0/yes/no or empty)
            
        Returns:
            Boolean value, defaults to False for empty string
        """
        if not value:
            return False
        
        true_values = ['true', '1', 'yes']
        false_values = ['false', '0', 'no']
        
        if value in true_values:
            return True
        elif value in false_values:
            return False
        else:
            # Return False as default, validator will catch invalid values
            return False
    
    def import_questions(self, duplicate_strategy: Dict[str, str] = None) -> ImportResult:
        """Create Question objects with specified duplicate handling.
        
        Args:
            duplicate_strategy: Dict mapping question identifiers to strategy
                               ('skip', 'replace', or 'rename')
                               Key format: "{question_name}|{question_type_name}"
                               
        Returns:
            ImportResult with counts and any errors
        """
        from django.db import transaction, IntegrityError, OperationalError
        
        if duplicate_strategy is None:
            duplicate_strategy = {}
        
        errors = []
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        try:
            # Parse and validate questions
            questions = self.parse_questions()
            validation_result = self.validate()
            
            if not validation_result['is_valid']:
                error_messages = [
                    f"Row {err.row_number}, {err.field}: {err.message}"
                    for err in validation_result['errors']
                ]
                return ImportResult(
                    success=False,
                    created_count=0,
                    updated_count=0,
                    skipped_count=0,
                    errors=error_messages
                )
            
            # Check for duplicates
            duplicates = self.validator.check_duplicates(questions, self.target_survey)
            duplicate_map = {
                f"{dup.question_data.question_name}|{dup.question_data.question_type_name}": dup
                for dup in duplicates
            }
            
            # Begin transaction with database error handling
            try:
                with transaction.atomic():
                    for question_data in questions:
                        key = f"{question_data.question_name}|{question_data.question_type_name}"
                        
                        # Check if this is a duplicate
                        if key in duplicate_map:
                            duplicate = duplicate_map[key]
                            strategy = duplicate_strategy.get(key, 'skip')
                            
                            if strategy == 'skip':
                                # Skip strategy: do not create question
                                skipped_count += 1
                                continue
                                
                            elif strategy == 'replace':
                                # Replace strategy: update existing question
                                existing = duplicate.existing_question
                                
                                # Update param_values
                                existing._param_values = '|'.join(question_data.param_values)
                                
                                # Update sequence if provided
                                if question_data.sequence is not None:
                                    existing.seq = question_data.sequence
                                
                                try:
                                    existing.save()
                                    updated_count += 1
                                except IntegrityError as e:
                                    raise ValueError(f"Database integrity error updating question '{question_data.question_name}': {str(e)}")
                                continue
                                
                            elif strategy == 'rename':
                                # Rename strategy: append suffix and create new question
                                # Find a unique name by appending a suffix
                                base_name = question_data.question_name
                                suffix = 1
                                new_name = f"{base_name}_{suffix}"
                                
                                # Keep incrementing suffix until we find a unique name
                                while Question.objects.filter(
                                    survey=self.target_survey,
                                    name=new_name,
                                    question_type__name=question_data.question_type_name
                                ).exists():
                                    suffix += 1
                                    new_name = f"{base_name}_{suffix}"
                                
                                # Create with new name
                                question_data.question_name = new_name
                        
                        # Create new question (either not a duplicate or renamed)
                        try:
                            self._create_question(question_data)
                            created_count += 1
                        except IntegrityError as e:
                            raise ValueError(f"Database integrity error creating question '{question_data.question_name}': {str(e)}")
                        except Question.DoesNotExist:
                            raise ValueError(f"Question type '{question_data.question_type_name}' not found in database")
                            
            except OperationalError as e:
                return ImportResult(
                    success=False,
                    created_count=0,
                    updated_count=0,
                    skipped_count=0,
                    errors=[f"Database connection error: {str(e)}. Please try again later."]
                )
            except IntegrityError as e:
                return ImportResult(
                    success=False,
                    created_count=0,
                    updated_count=0,
                    skipped_count=0,
                    errors=[f"Database integrity error: {str(e)}"]
                )
            
            return ImportResult(
                success=True,
                created_count=created_count,
                updated_count=updated_count,
                skipped_count=skipped_count,
                errors=[]
            )
            
        except ValueError as e:
            # CSV parsing or validation errors
            return ImportResult(
                success=False,
                created_count=0,
                updated_count=0,
                skipped_count=0,
                errors=[str(e)]
            )
        except Exception as e:
            # Catch-all for unexpected errors
            return ImportResult(
                success=False,
                created_count=0,
                updated_count=0,
                skipped_count=0,
                errors=[f"Unexpected error during import: {str(e)}"]
            )
    
    def _create_question(self, question_data: QuestionData):
        """Create a Question object from QuestionData.
        
        Args:
            question_data: QuestionData object with question information
        """
        # Get the QuestionType
        question_type = QuestionType.objects.get(name=question_data.question_type_name)
        
        # Determine sequence
        if question_data.sequence is not None:
            seq = question_data.sequence
        else:
            # Auto-assign sequence starting from max existing + 1
            max_seq = Question.objects.filter(
                survey=self.target_survey
            ).aggregate(models.Max('seq'))['seq__max']
            seq = (max_seq or 0) + 1
        
        # Create the question
        question = Question.objects.create(
            survey=self.target_survey,
            name=question_data.question_name,
            question_type=question_type,
            _param_values='|'.join(question_data.param_values),
            per_class=question_data.per_class,
            seq=seq
        )
        
        return question


class QuestionValidator:
    """Validates question data against business rules."""
    
    def check_duplicates(self, questions: List[QuestionData], survey) -> List[Duplicate]:
        """Identify duplicate questions in target survey.
        
        A question is considered a duplicate if both question_name AND question_type
        match an existing question in the survey.
        
        Args:
            questions: List of QuestionData objects to check
            survey: Survey object to check against
            
        Returns:
            List of Duplicate objects with existing questions
        """
        duplicates = []
        
        for question_data in questions:
            try:
                existing_question = Question.objects.get(
                    survey=survey,
                    name=question_data.question_name,
                    question_type__name=question_data.question_type_name
                )
                duplicates.append(Duplicate(
                    question_data=question_data,
                    existing_question=existing_question
                ))
            except Question.DoesNotExist:
                # Not a duplicate
                pass
            except Question.MultipleObjectsReturned:
                # Multiple duplicates exist - get the first one
                existing_question = Question.objects.filter(
                    survey=survey,
                    name=question_data.question_name,
                    question_type__name=question_data.question_type_name
                ).first()
                duplicates.append(Duplicate(
                    question_data=question_data,
                    existing_question=existing_question
                ))
        
        return duplicates
    
    def validate_row(self, row_num: int, row_data: Dict) -> List[ValidationError]:
        """Validate a single CSV row.
        
        Args:
            row_num: Row number in CSV file
            row_data: Dictionary with question data
            
        Returns:
            List of ValidationError objects (empty if valid)
        """
        errors = []
        
        # Validate question_name
        question_name = row_data.get('question_name', '')
        if not question_name:
            errors.append(ValidationError(
                row_number=row_num,
                field='question_name',
                message='Question name is required'
            ))
        elif len(question_name) > 255:
            errors.append(ValidationError(
                row_number=row_num,
                field='question_name',
                message=f'Question name exceeds 255 characters (length: {len(question_name)})'
            ))
        
        # Validate question_type exists
        question_type_name = row_data.get('question_type', '')
        if not question_type_name:
            errors.append(ValidationError(
                row_number=row_num,
                field='question_type',
                message='Question type is required'
            ))
        else:
            try:
                question_type = QuestionType.objects.get(name=question_type_name)
                
                # Validate param_values count against param_names
                param_values = row_data.get('param_values', [])
                if not isinstance(param_values, list):
                    param_values = []
                
                param_names = question_type.param_names
                if len(param_values) < len(param_names):
                    errors.append(ValidationError(
                        row_number=row_num,
                        field='param_values',
                        message=f"Question type '{question_type_name}' requires {len(param_names)} parameters but only {len(param_values)} provided"
                    ))
                    
            except QuestionType.DoesNotExist:
                errors.append(ValidationError(
                    row_number=row_num,
                    field='question_type',
                    message=f"Question type '{question_type_name}' does not exist"
                ))
        
        # Validate per_class
        # Note: per_class is already converted to boolean in parse_questions,
        # but we need to validate the original string value
        # We'll check if it's a boolean (already parsed) or a string (needs validation)
        per_class_value = row_data.get('per_class', '')
        if isinstance(per_class_value, str):
            per_class_str = per_class_value.strip().lower()
            if per_class_str:
                valid_per_class = ['true', 'false', '1', '0', 'yes', 'no']
                if per_class_str not in valid_per_class:
                    errors.append(ValidationError(
                        row_number=row_num,
                        field='per_class',
                        message=f"per_class must be true/false/1/0/yes/no or empty, got '{per_class_str}'"
                    ))
        
        # Validate sequence
        sequence = row_data.get('sequence')
        if sequence is not None and sequence != '':
            if isinstance(sequence, str):
                errors.append(ValidationError(
                    row_number=row_num,
                    field='sequence',
                    message=f"Sequence must be a positive integer, got '{sequence}'"
                ))
            elif not isinstance(sequence, int) or sequence <= 0:
                errors.append(ValidationError(
                    row_number=row_num,
                    field='sequence',
                    message=f"Sequence must be a positive integer, got '{sequence}'"
                ))
        
        return errors


class TemplateManager:
    """Manages predefined question templates."""
    
    TEMPLATE_DIR = 'esp/survey/fixtures/question_templates/'
    
    @classmethod
    def list_templates(cls, category: str = None):
        """List available templates, optionally filtered by category.
        
        Args:
            category: Optional category filter (e.g., 'student', 'teacher')
            
        Returns:
            List of template filenames (without path)
        """
        import os
        from django.conf import settings
        
        # Build full path to template directory
        template_path = os.path.join(settings.PROJECT_ROOT, cls.TEMPLATE_DIR)
        
        # Check if directory exists
        if not os.path.exists(template_path):
            return []
        
        # List all CSV files in the directory
        templates = []
        for filename in os.listdir(template_path):
            if filename.endswith('.csv'):
                # Filter by category if specified
                if category is None:
                    templates.append(filename)
                else:
                    # Template naming convention: {category}_{description}.csv
                    if filename.startswith(f"{category}_"):
                        templates.append(filename)
        
        return sorted(templates)
    
    @classmethod
    def load_template(cls, template_name: str, target_survey=None):
        """Load template as CSVQuestionImporter instance.
        
        Args:
            template_name: Name of the template file (with or without .csv extension)
            target_survey: Optional Survey object to import into
            
        Returns:
            CSVQuestionImporter instance initialized with template data
            
        Raises:
            FileNotFoundError: If template file does not exist
        """
        import os
        from django.conf import settings
        
        # Ensure .csv extension
        if not template_name.endswith('.csv'):
            template_name = f"{template_name}.csv"
        
        # Build full path to template file
        template_path = os.path.join(
            settings.PROJECT_ROOT,
            cls.TEMPLATE_DIR,
            template_name
        )
        
        # Check if file exists
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template '{template_name}' not found at {template_path}")
        
        # Read template file
        with open(template_path, 'r', encoding='utf-8') as f:
            csv_content = f.read()
        
        # Return CSVQuestionImporter instance
        return CSVQuestionImporter(csv_content, target_survey)


class ImportLogger:
    """Logs import operations for audit trail."""
    
    def __init__(self):
        """Initialize logger with Django logging framework."""
        import logging
        import json
        self.logger = logging.getLogger('esp.survey.import')
        self.json = json
    
    def log_start(self, user, surveys, source):
        """Record import session start.
        
        Args:
            user: Admin user performing the import
            surveys: List of Survey objects being imported into
            source: String describing import source ('upload' or template name)
        """
        from django.utils import timezone
        
        survey_names = [survey.name for survey in surveys]
        
        log_data = {
            'event': 'import_start',
            'timestamp': timezone.now().isoformat(),
            'admin_user': user.username if user else 'unknown',
            'admin_user_id': user.id if user else None,
            'target_surveys': survey_names,
            'survey_count': len(surveys),
            'source': source
        }
        
        self.logger.info(self.json.dumps(log_data))
    
    def log_complete(self, created, updated, skipped):
        """Record successful completion.
        
        Args:
            created: Count of questions created
            updated: Count of questions updated
            skipped: Count of questions skipped
        """
        from django.utils import timezone
        
        log_data = {
            'event': 'import_complete',
            'timestamp': timezone.now().isoformat(),
            'status': 'success',
            'questions_created': created,
            'questions_updated': updated,
            'questions_skipped': skipped,
            'total_processed': created + updated + skipped
        }
        
        self.logger.info(self.json.dumps(log_data))
    
    def log_failure(self, errors):
        """Record validation or execution failures.
        
        Args:
            errors: List of error messages or ValidationError objects
        """
        from django.utils import timezone
        
        # Convert ValidationError objects to strings if needed
        error_messages = []
        for error in errors:
            if isinstance(error, ValidationError):
                error_messages.append(f"Row {error.row_number}, {error.field}: {error.message}")
            else:
                error_messages.append(str(error))
        
        log_data = {
            'event': 'import_failure',
            'timestamp': timezone.now().isoformat(),
            'status': 'failed',
            'error_count': len(error_messages),
            'errors': error_messages
        }
        
        self.logger.error(self.json.dumps(log_data))
