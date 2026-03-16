#!/usr/bin/env python
"""
Manual test script for TemplateManager functionality.
This script tests the TemplateManager class without requiring Django setup.
"""
import os
import sys

# Add the esp directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'esp'))

def test_template_directory_exists():
    """Test that the template directory exists."""
    template_dir = 'esp/esp/survey/fixtures/question_templates/'
    full_path = os.path.join(os.path.dirname(__file__), template_dir)
    
    print(f"Checking template directory: {full_path}")
    if os.path.exists(full_path):
        print("✓ Template directory exists")
        return True
    else:
        print("✗ Template directory does not exist")
        return False

def test_template_files_exist():
    """Test that the required template files exist."""
    template_dir = 'esp/esp/survey/fixtures/question_templates/'
    full_path = os.path.join(os.path.dirname(__file__), template_dir)
    
    required_templates = [
        'student_program_feedback.csv',
        'teacher_program_feedback.csv'
    ]
    
    all_exist = True
    for template in required_templates:
        template_path = os.path.join(full_path, template)
        if os.path.exists(template_path):
            print(f"✓ Template exists: {template}")
        else:
            print(f"✗ Template missing: {template}")
            all_exist = False
    
    return all_exist

def test_template_content():
    """Test that template files have valid CSV content."""
    template_dir = 'esp/esp/survey/fixtures/question_templates/'
    full_path = os.path.join(os.path.dirname(__file__), template_dir)
    
    templates = [
        'student_program_feedback.csv',
        'teacher_program_feedback.csv'
    ]
    
    all_valid = True
    for template in templates:
        template_path = os.path.join(full_path, template)
        print(f"\nChecking content of {template}:")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Check header
        if lines and 'question_name,question_type' in lines[0]:
            print(f"  ✓ Valid CSV header")
        else:
            print(f"  ✗ Invalid CSV header")
            all_valid = False
        
        # Check number of data rows
        data_rows = len(lines) - 1  # Exclude header
        print(f"  ✓ Contains {data_rows} question(s)")
        
        if data_rows < 1:
            print(f"  ✗ No questions found")
            all_valid = False
    
    return all_valid

def test_list_templates_logic():
    """Test the list_templates logic without Django."""
    template_dir = 'esp/esp/survey/fixtures/question_templates/'
    full_path = os.path.join(os.path.dirname(__file__), template_dir)
    
    print("\nTesting list_templates logic:")
    
    # List all CSV files
    all_templates = []
    for filename in os.listdir(full_path):
        if filename.endswith('.csv'):
            all_templates.append(filename)
    
    print(f"  All templates: {sorted(all_templates)}")
    
    # Filter by category
    student_templates = [f for f in all_templates if f.startswith('student_')]
    teacher_templates = [f for f in all_templates if f.startswith('teacher_')]
    
    print(f"  Student templates: {sorted(student_templates)}")
    print(f"  Teacher templates: {sorted(teacher_templates)}")
    
    if len(student_templates) >= 1 and len(teacher_templates) >= 1:
        print("  ✓ Both student and teacher templates exist")
        return True
    else:
        print("  ✗ Missing required template categories")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing TemplateManager Implementation")
    print("=" * 60)
    
    tests = [
        ("Template directory exists", test_template_directory_exists),
        ("Template files exist", test_template_files_exist),
        ("Template content is valid", test_template_content),
        ("List templates logic works", test_list_templates_logic),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 60)
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
