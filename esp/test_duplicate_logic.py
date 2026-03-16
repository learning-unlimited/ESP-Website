#!/usr/bin/env python
"""
Simple test script to verify duplicate detection and resolution logic
without requiring full Django test setup.
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esp.settings')

import django
django.setup()

from esp.survey.importers import CSVQuestionImporter, QuestionValidator, QuestionData
from esp.survey.models import Survey, QuestionType, Question
from esp.program.models import Program

def test_duplicate_detection():
    """Test duplicate detection logic."""
    print("Testing duplicate detection...")
    
    # Create test data
    program = Program.objects.create(grade_min=7, grade_max=12)
    survey = Survey.objects.create(
        name='Test Survey',
        program=program,
        category='learn',
    )
    
    qt_yesno = QuestionType.objects.create(
        name='Yes/No Test',
        _param_names='',
        is_numeric=False,
        is_countable=False,
    )
    
    # Create an existing question
    existing = Question.objects.create(
        survey=survey,
        name='Existing Question',
        question_type=qt_yesno,
        _param_values='',
        per_class=False,
        seq=1
    )
    
    # Test duplicate detection
    validator = QuestionValidator()
    questions = [
        QuestionData(
            row_number=2,
            question_name='Existing Question',
            question_type_name='Yes/No Test',
            param_values=[],
            per_class=False,
            sequence=None
        )
    ]
    
    duplicates = validator.check_duplicates(questions, survey)
    
    assert len(duplicates) == 1, f"Expected 1 duplicate, got {len(duplicates)}"
    assert duplicates[0].existing_question.id == existing.id
    print("✓ Duplicate detection works correctly")
    
    # Clean up
    Question.objects.all().delete()
    QuestionType.objects.all().delete()
    Survey.objects.all().delete()
    Program.objects.all().delete()


def test_skip_strategy():
    """Test skip strategy."""
    print("\nTesting skip strategy...")
    
    # Create test data
    program = Program.objects.create(grade_min=7, grade_max=12)
    survey = Survey.objects.create(
        name='Test Survey',
        program=program,
        category='learn',
    )
    
    qt_yesno = QuestionType.objects.create(
        name='Yes/No Test2',
        _param_names='',
        is_numeric=False,
        is_countable=False,
    )
    
    # Create an existing question
    existing = Question.objects.create(
        survey=survey,
        name='Skip Question',
        question_type=qt_yesno,
        _param_values='',
        per_class=False,
        seq=1
    )
    
    csv_data = """question_name,question_type
Skip Question,Yes/No Test2"""
    
    importer = CSVQuestionImporter(csv_data, survey)
    
    duplicate_strategy = {
        'Skip Question|Yes/No Test2': 'skip'
    }
    
    result = importer.import_questions(duplicate_strategy)
    
    assert result.success, f"Import failed: {result.errors}"
    assert result.created_count == 0, f"Expected 0 created, got {result.created_count}"
    assert result.skipped_count == 1, f"Expected 1 skipped, got {result.skipped_count}"
    assert result.updated_count == 0, f"Expected 0 updated, got {result.updated_count}"
    
    # Verify no new question created
    count = Question.objects.filter(survey=survey).count()
    assert count == 1, f"Expected 1 question, got {count}"
    
    print("✓ Skip strategy works correctly")
    
    # Clean up
    Question.objects.all().delete()
    QuestionType.objects.all().delete()
    Survey.objects.all().delete()
    Program.objects.all().delete()


def test_replace_strategy():
    """Test replace strategy."""
    print("\nTesting replace strategy...")
    
    # Create test data
    program = Program.objects.create(grade_min=7, grade_max=12)
    survey = Survey.objects.create(
        name='Test Survey',
        program=program,
        category='learn',
    )
    
    qt_rating = QuestionType.objects.create(
        name='Rating Test',
        _param_names='min|max',
        is_numeric=True,
        is_countable=True,
    )
    
    # Create an existing question
    existing = Question.objects.create(
        survey=survey,
        name='Replace Question',
        question_type=qt_rating,
        _param_values='1|5',
        per_class=False,
        seq=1
    )
    
    csv_data = """question_name,question_type,param_values,sequence
Replace Question,Rating Test,1|10,5"""
    
    importer = CSVQuestionImporter(csv_data, survey)
    
    duplicate_strategy = {
        'Replace Question|Rating Test': 'replace'
    }
    
    result = importer.import_questions(duplicate_strategy)
    
    assert result.success, f"Import failed: {result.errors}"
    assert result.created_count == 0, f"Expected 0 created, got {result.created_count}"
    assert result.skipped_count == 0, f"Expected 0 skipped, got {result.skipped_count}"
    assert result.updated_count == 1, f"Expected 1 updated, got {result.updated_count}"
    
    # Verify existing question updated
    existing.refresh_from_db()
    assert existing._param_values == '1|10', f"Expected '1|10', got '{existing._param_values}'"
    assert existing.seq == 5, f"Expected seq=5, got seq={existing.seq}"
    
    # Verify no new question created
    count = Question.objects.filter(survey=survey).count()
    assert count == 1, f"Expected 1 question, got {count}"
    
    print("✓ Replace strategy works correctly")
    
    # Clean up
    Question.objects.all().delete()
    QuestionType.objects.all().delete()
    Survey.objects.all().delete()
    Program.objects.all().delete()


def test_rename_strategy():
    """Test rename strategy."""
    print("\nTesting rename strategy...")
    
    # Create test data
    program = Program.objects.create(grade_min=7, grade_max=12)
    survey = Survey.objects.create(
        name='Test Survey',
        program=program,
        category='learn',
    )
    
    qt_yesno = QuestionType.objects.create(
        name='Yes/No Test3',
        _param_names='',
        is_numeric=False,
        is_countable=False,
    )
    
    # Create an existing question
    existing = Question.objects.create(
        survey=survey,
        name='Rename Question',
        question_type=qt_yesno,
        _param_values='',
        per_class=False,
        seq=1
    )
    
    csv_data = """question_name,question_type,sequence
Rename Question,Yes/No Test3,2"""
    
    importer = CSVQuestionImporter(csv_data, survey)
    
    duplicate_strategy = {
        'Rename Question|Yes/No Test3': 'rename'
    }
    
    result = importer.import_questions(duplicate_strategy)
    
    assert result.success, f"Import failed: {result.errors}"
    assert result.created_count == 1, f"Expected 1 created, got {result.created_count}"
    assert result.skipped_count == 0, f"Expected 0 skipped, got {result.skipped_count}"
    assert result.updated_count == 0, f"Expected 0 updated, got {result.updated_count}"
    
    # Verify existing question unchanged
    existing.refresh_from_db()
    assert existing.name == 'Rename Question', f"Expected 'Rename Question', got '{existing.name}'"
    assert existing.seq == 1, f"Expected seq=1, got seq={existing.seq}"
    
    # Verify new question created with suffix
    count = Question.objects.filter(survey=survey).count()
    assert count == 2, f"Expected 2 questions, got {count}"
    
    new_question = Question.objects.get(survey=survey, seq=2)
    assert new_question.name == 'Rename Question_1', f"Expected 'Rename Question_1', got '{new_question.name}'"
    
    print("✓ Rename strategy works correctly")
    
    # Clean up
    Question.objects.all().delete()
    QuestionType.objects.all().delete()
    Survey.objects.all().delete()
    Program.objects.all().delete()


if __name__ == '__main__':
    try:
        test_duplicate_detection()
        test_skip_strategy()
        test_replace_strategy()
        test_rename_strategy()
        print("\n✅ All tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
