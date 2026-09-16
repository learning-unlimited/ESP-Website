from django import forms

from esp.survey.models  import Question, Survey

class SurveyForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, commit=True, program = None, *args, **kwargs):
        survey = super().save(commit=False, *args, **kwargs)
        survey.program = program
        if commit:
            survey.save()
        return survey

    class Meta:
        model = Survey
        exclude = ['program']

class QuestionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        cur_prog = kwargs.pop('cur_prog', None)
        surveys = Survey.objects.filter(program=cur_prog)
        self.base_fields['survey'].choices = ((str(survey.id), survey.name + " (" + survey.category + ")") for survey in surveys)
        super().__init__(*args, **kwargs)
        instance = kwargs.pop('instance', None)
        if instance:
            self.base_fields['survey'].initial = str(instance.id)

    class Meta:
        model = Question
        exclude = ['param_values']
        help_texts = {
            'name': ('This is the question that will be displayed to the user'),
            'per_class': ('Should this question be shown once for each class?'),
            'seq': ('Determines the order of the questions'),
            '_param_values': (),
        }
        labels = {
            'name': ('Question'),
            'question_type': ('Question Type'),
            'per_class': ('Per Class'),
            '_param_values': ('Parameter Values'),
            'seq': ('Sequence'),
        }

class SurveyImportForm(forms.Form):
    survey_id = forms.ModelChoiceField(queryset=None, label = "Survey")

    def __init__(self, *args, **kwargs):
        cur_prog = kwargs.pop('cur_prog', None)
        super().__init__(*args, **kwargs)
        self.fields['survey_id'].queryset = Survey.objects.exclude(program=cur_prog)

class CSVQuestionImportForm(forms.Form):
    csv_file = forms.FileField(label="CSV File", help_text="Upload a CSV file with survey questions.")
    survey = forms.ModelChoiceField(queryset=None, label="Target Survey")

    def __init__(self, *args, **kwargs):
        cur_prog = kwargs.pop('cur_prog', None)
        super().__init__(*args, **kwargs)
        if cur_prog:
            self.fields['survey'].queryset = Survey.objects.filter(program=cur_prog)
        else:
            self.fields['survey'].queryset = Survey.objects.none()


def parse_csv(csv_file):
    """Parse and validate a CSV file of survey questions.

    Expected columns: question_text, question_type
    Optional columns: per_class, seq, param_values

    Returns a tuple of (parsed_rows, errors) where:
      - parsed_rows is a list of dicts with validated data
      - errors is a list of dicts with row_number and message
    """
    import csv
    import io

    from esp.survey.models import QuestionType

    parsed_rows = []
    errors = []

    # Check if the file is a valid CSV by attempting to read it
    try:
        content = csv_file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        # Try to detect if it's a binary file (like Excel, Numbers, etc.)
        csv_file.seek(0)
        first_bytes = csv_file.read(8)

        # Check for common binary file signatures
        if first_bytes.startswith(b'PK\x03\x04'):  # ZIP-based formats (xlsx, numbers, etc.)
            errors.append({
                'row_number': 0,
                'message': 'The uploaded file appears to be a spreadsheet file (Excel, Numbers, etc.). Please export it as a CSV file and try again.'
            })
        elif first_bytes.startswith(b'\xd0\xcf\x11\xe0'):  # Old Excel format
            errors.append({
                'row_number': 0,
                'message': 'The uploaded file appears to be an Excel file. Please save it as a CSV file and try again.'
            })
        else:
            errors.append({
                'row_number': 0,
                'message': 'The uploaded file is not a valid CSV file. Please ensure the file is saved in CSV (Comma Separated Values) format.'
            })
        return parsed_rows, errors
    except Exception as e:
        errors.append({
            'row_number': 0,
            'message': f'Error reading file: {str(e)}. Please ensure the file is a valid CSV file.'
        })
        return parsed_rows, errors

    reader = csv.DictReader(io.StringIO(content))

    # Validate required columns
    if reader.fieldnames is None:
        errors.append({'row_number': 0, 'message': 'CSV file is empty or has no header row.'})
        return parsed_rows, errors

    fieldnames_lower = [f.strip().lower() for f in reader.fieldnames]
    required_columns = ['question_text', 'question_type']
    missing = [col for col in required_columns if col not in fieldnames_lower]
    if missing:
        errors.append({
            'row_number': 0,
            'message': 'Missing required columns: %s' % ', '.join(missing),
        })
        return parsed_rows, errors

    # Build a case-insensitive lookup for QuestionType names
    question_types = {}
    duplicate_qtype_names = set()
    for qt in QuestionType.objects.all():
        key = qt.name.lower()
        if key in question_types and question_types[key].id != qt.id:
            duplicate_qtype_names.add(key)
        else:
            question_types[key] = qt

    # If there are duplicate QuestionType names (case-insensitive), fail fast
    if duplicate_qtype_names:
        errors.append({
            'row_number': 0,
            'message': ('Multiple QuestionType entries share the same name (case-insensitive): %s. '
                       'Please resolve these duplicates before importing.') % ', '.join(sorted(duplicate_qtype_names)),
        })
        return parsed_rows, errors

    # Normalize fieldnames for lookup
    col_map = {f.strip().lower(): f for f in reader.fieldnames}

    for row_number, row in enumerate(reader, start=2):
        row_errors = []

        # Extract values using normalized column names
        question_text = row.get(col_map.get('question_text', ''), '').strip()
        question_type_name = row.get(col_map.get('question_type', ''), '').strip()
        per_class_str = row.get(col_map.get('per_class', ''), '').strip().lower()
        seq_str = row.get(col_map.get('seq', ''), '').strip()
        param_values = row.get(col_map.get('param_values', ''), '').strip()

        # Validate question_text
        if not question_text:
            row_errors.append('question_text is empty')

        # Validate question_type
        question_type = None
        if not question_type_name:
            row_errors.append('question_type is empty')
        else:
            question_type = question_types.get(question_type_name.lower())
            if question_type is None:
                row_errors.append(
                    'Unknown question_type "%s". Valid types: %s'
                    % (question_type_name, ', '.join(sorted(question_types.keys())))
                )

        # Validate per_class
        per_class = False
        if per_class_str:
            if per_class_str in ('true', 'yes', '1'):
                per_class = True
            elif per_class_str in ('false', 'no', '0'):
                per_class = False
            else:
                row_errors.append(
                    'Invalid per_class value "%s". Use true/false, yes/no, or 1/0.'
                    % per_class_str
                )

        # Validate seq
        seq = 0
        if seq_str:
            try:
                seq = int(seq_str)
            except ValueError:
                row_errors.append('Invalid seq value "%s". Must be an integer.' % seq_str)

        if row_errors:
            errors.append({
                'row_number': row_number,
                'message': '; '.join(row_errors),
            })
        else:
            parsed_rows.append({
                'row_number': row_number,
                'question_text': question_text,
                'question_type': question_type,
                'per_class': per_class,
                'seq': seq,
                'param_values': param_values,
            })

    return parsed_rows, errors
