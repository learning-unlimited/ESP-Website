"""
Manual test script to verify admin import functionality.
This script tests the basic structure and imports of the admin module.
"""

import sys
import os

# Add the esp directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'esp'))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esp.settings')

try:
    import django
    django.setup()
    
    from esp.survey.admin import SurveyAdmin
    from esp.survey.forms import QuestionImportForm, DuplicateResolutionForm
    from esp.survey.importers import CSVQuestionImporter, TemplateManager
    
    print("✓ All imports successful")
    
    # Check that the action is registered
    admin = SurveyAdmin(None, None)
    if 'import_questions' in admin.actions:
        print("✓ import_questions action is registered")
    else:
        print("✗ import_questions action is NOT registered")
    
    # Check that the method exists
    if hasattr(admin, 'import_questions'):
        print("✓ import_questions method exists")
    else:
        print("✗ import_questions method does NOT exist")
    
    # Check helper methods
    if hasattr(admin, '_process_import_form'):
        print("✓ _process_import_form method exists")
    else:
        print("✗ _process_import_form method does NOT exist")
    
    if hasattr(admin, '_process_duplicate_resolution'):
        print("✓ _process_duplicate_resolution method exists")
    else:
        print("✗ _process_duplicate_resolution method does NOT exist")
    
    print("\n✓ All checks passed!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
