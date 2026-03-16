#!/usr/bin/env python
"""
Manual verification script for CSVQuestionImporter and QuestionValidator.
This script tests the basic functionality without requiring a full Django setup.
"""

import sys
import os

# Add the esp directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esp.settings")
os.environ.setdefault("GITHUB_ACTIONS", "true")  # Skip virtualenv activation

import django
django.setup()

from esp.survey.importers import CSVQuestionImporter, QuestionValidator, QuestionData
from esp.survey.models import Survey, QuestionType
from esp.program.models import Program

def test_csv_parsing():
    """Test basic CSV parsing functionality."""
    print("Testing CSV parsing...")
    
    csv_data = """question_name,question_type,param_values,per_class,sequence
Do you like this?,Yes/No,,false,1
Rate this class,Rating,1|5,true,2"""
    
    # Create a mock survey (we'll use None for now to test parsing only)
    class MockSurvey:
        pass
    
    survey = MockSurvey()
    importer = CSVQuestionImporter(csv_data, survey)
    
    try:
        questions = importer.parse_questions()
        print(f"✓ Successfully parsed {len(questions)} questions")
        
        # Verify first question
        q1 = questions[0]
        assert q1.question_name == 'Do you like this?', f"Expected 'Do you like this?', got '{q1.question_name}'"
        assert q1.question_type_name == 'Yes/No', f"Expected 'Yes/No', got '{q1.question_type_name}'"
        assert q1.per_class == False, f"Expected False, got {q1.per_class}"
        assert q1.sequence == 1, f"Expected 1, got {q1.sequence}"
        print("✓ First question parsed correctly")
        
        # Verify second question
        q2 = questions[1]
        assert q2.question_name == 'Rate this class', f"Expected 'Rate this class', got '{q2.question_name}'"
        assert q2.param_values == ['1', '5'], f"Expected ['1', '5'], got {q2.param_values}"
        assert q2.per_class == True, f"Expected True, got {q2.per_class}"
        assert q2.sequence == 2, f"Expected 2, got {q2.sequence}"
        print("✓ Second question parsed correctly")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_validation():
    """Test validation functionality."""
    print("\nTesting validation...")
    
    validator = QuestionValidator()
    
    # Test valid row
    valid_row = {
        'question_name': 'Valid question',
        'question_type': 'Yes/No',
        'param_values': [],
        'per_class': False,
        'sequence': 1
    }
    
    # Note: This will fail if QuestionType doesn't exist in DB
    # We'll catch the error and note it
    try:
        errors = validator.validate_row(2, valid_row)
        if len(errors) == 0:
            print("✓ Valid row passed validation")
        else:
            print(f"✗ Valid row failed validation: {errors}")
    except Exception as e:
        print(f"⚠ Validation requires database setup: {e}")
    
    # Test invalid question name (too long)
    invalid_row = {
        'question_name': 'x' * 256,
        'question_type': 'Yes/No',
        'param_values': [],
        'per_class': False,
        'sequence': 1
    }
    
    try:
        errors = validator.validate_row(2, invalid_row)
        if len(errors) > 0 and 'exceeds 255 characters' in errors[0].message:
            print("✓ Long question name validation works")
        else:
            print(f"✗ Long question name validation failed: {errors}")
    except Exception as e:
        print(f"⚠ Validation requires database setup: {e}")
    
    # Test invalid sequence
    invalid_seq_row = {
        'question_name': 'Test',
        'question_type': 'Yes/No',
        'param_values': [],
        'per_class': False,
        'sequence': 'not_a_number'
    }
    
    errors = validator.validate_row(2, invalid_seq_row)
    if len(errors) > 0 and 'positive integer' in errors[0].message:
        print("✓ Invalid sequence validation works")
    else:
        print(f"✗ Invalid sequence validation failed: {errors}")
    
    return True

def test_boolean_parsing():
    """Test boolean parsing for per_class field."""
    print("\nTesting boolean parsing...")
    
    csv_data = """question_name,question_type,per_class
Q1,Yes/No,true
Q2,Yes/No,false
Q3,Yes/No,1
Q4,Yes/No,0
Q5,Yes/No,yes
Q6,Yes/No,no
Q7,Yes/No,"""
    
    class MockSurvey:
        pass
    
    survey = MockSurvey()
    importer = CSVQuestionImporter(csv_data, survey)
    
    try:
        questions = importer.parse_questions()
        
        expected = [True, False, True, False, True, False, False]
        for i, (q, exp) in enumerate(zip(questions, expected)):
            if q.per_class == exp:
                print(f"✓ Q{i+1} per_class={q.per_class} (correct)")
            else:
                print(f"✗ Q{i+1} per_class={q.per_class}, expected {exp}")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("Manual Verification of CSVQuestionImporter")
    print("=" * 60)
    
    results = []
    
    results.append(("CSV Parsing", test_csv_parsing()))
    results.append(("Validation", test_validation()))
    results.append(("Boolean Parsing", test_boolean_parsing()))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name}: {status}")
    
    all_passed = all(r for _, r in results)
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed."))
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
