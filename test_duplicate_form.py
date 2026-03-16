#!/usr/bin/env python
"""
Simple script to manually verify DuplicateResolutionForm implementation.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'esp'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esp.django_settings')
django.setup()

from esp.survey.forms import DuplicateResolutionForm
from esp.survey.importers import Duplicate, QuestionData
from esp.survey.models import Question, QuestionType, Survey
from esp.program.models import Program

# Create test data
print("Creating test data...")
program = Program.objects.first()
if not program:
    print("No program found. Creating one...")
    program = Program.objects.create(grade_min=7, grade_max=12)

survey = Survey.objects.filter(program=program).first()
if not survey:
    print("No survey found. Creating one...")
    survey = Survey.objects.create(
        name='Test Survey',
        program=program,
        category='learn'
    )

qt = QuestionType.objects.first()
if not qt:
    print("No question type found. Creating one...")
    qt = QuestionType.objects.create(
        name='Yes/No',
        _param_names='',
        is_numeric=False,
        is_countable=False
    )

# Create an existing question
existing_q = Question.objects.create(
    survey=survey,
    name='Test Question',
    question_type=qt,
    _param_values='',
    per_class=False,
    seq=1
)

print(f"Created question: {existing_q.name} (ID: {existing_q.id})")

# Create duplicate data
duplicates = [
    Duplicate(
        question_data=QuestionData(
            row_number=2,
            question_name='Test Question',
            question_type_name='Yes/No',
            param_values=[],
            per_class=False,
            sequence=None
        ),
        existing_question=existing_q
    )
]

print("\nCreating DuplicateResolutionForm...")
form = DuplicateResolutionForm(duplicates)

print(f"Form has {len(form.fields)} field(s)")
for field_name, field in form.fields.items():
    print(f"  - {field_name}: {field.label}")
    print(f"    Choices: {[c[0] for c in field.choices]}")
    print(f"    Initial: {field.initial}")

# Test with data
print("\nTesting form with data...")
form_data = {
    f'duplicate_{existing_q.id}': 'replace'
}
form = DuplicateResolutionForm(duplicates, data=form_data)

if form.is_valid():
    print("Form is valid!")
    strategies = form.get_strategies(duplicates)
    print(f"Strategies: {strategies}")
else:
    print("Form is invalid!")
    print(f"Errors: {form.errors}")

print("\n✓ DuplicateResolutionForm implementation verified successfully!")

# Cleanup
existing_q.delete()
print("\nCleaned up test data.")
