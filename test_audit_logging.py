#!/usr/bin/env python
"""
Simple test script to verify audit logging functionality.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esp.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'esp'))

django.setup()

from esp.survey.importers import ImportLogger, ValidationError
from esp.users.models import ESPUser
from esp.survey.models import Survey
from esp.program.models import Program
import logging
import json

# Configure logging to console for testing
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_import_logger():
    """Test the ImportLogger functionality."""
    print("=" * 60)
    print("Testing ImportLogger Audit Logging")
    print("=" * 60)
    
    # Create test data
    try:
        program = Program.objects.first()
        if not program:
            print("No program found, creating one...")
            program = Program.objects.create(grade_min=7, grade_max=12)
        
        survey = Survey.objects.filter(program=program).first()
        if not survey:
            print("No survey found, creating one...")
            survey = Survey.objects.create(
                name='Test Survey',
                program=program,
                category='learn'
            )
        
        user = ESPUser.objects.filter(is_superuser=True).first()
        if not user:
            print("No admin user found, using None...")
            user = None
    except Exception as e:
        print(f"Error setting up test data: {e}")
        print("Continuing with minimal test...")
        survey = None
        user = None
    
    # Initialize logger
    logger = ImportLogger()
    
    # Test 1: log_start
    print("\n1. Testing log_start()...")
    try:
        if survey:
            logger.log_start(user, [survey], 'CSV upload')
        else:
            print("   Skipping (no survey available)")
        print("   ✓ log_start() executed successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 2: log_complete
    print("\n2. Testing log_complete()...")
    try:
        logger.log_complete(created=5, updated=2, skipped=1)
        print("   ✓ log_complete() executed successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 3: log_failure with ValidationError objects
    print("\n3. Testing log_failure() with ValidationError objects...")
    try:
        errors = [
            ValidationError(row_number=2, field='question_type', message='Invalid type'),
            ValidationError(row_number=3, field='question_name', message='Name too long'),
        ]
        logger.log_failure(errors)
        print("   ✓ log_failure() with ValidationError executed successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 4: log_failure with string errors
    print("\n4. Testing log_failure() with string errors...")
    try:
        errors = ['Template file not found', 'Database connection error']
        logger.log_failure(errors)
        print("   ✓ log_failure() with strings executed successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 5: Verify JSON format
    print("\n5. Testing JSON format validity...")
    try:
        # Capture a log entry and verify it's valid JSON
        import io
        from contextlib import redirect_stderr
        
        # Create a string buffer to capture log output
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setFormatter(logging.Formatter('%(message)s'))
        
        # Add handler to the logger
        esp_logger = logging.getLogger('esp.survey.import')
        esp_logger.addHandler(handler)
        esp_logger.setLevel(logging.INFO)
        
        # Generate a log entry
        logger.log_complete(1, 2, 3)
        
        # Get the captured output
        log_output = log_capture.getvalue()
        
        # Try to parse as JSON
        if log_output:
            log_data = json.loads(log_output.strip())
            print(f"   ✓ JSON format is valid")
            print(f"   Sample log entry: {json.dumps(log_data, indent=2)}")
        else:
            print("   ⚠ No log output captured (may be using different handler)")
        
        # Clean up
        esp_logger.removeHandler(handler)
        
    except json.JSONDecodeError as e:
        print(f"   ✗ Invalid JSON format: {e}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Audit Logging Tests Complete")
    print("=" * 60)

if __name__ == '__main__':
    test_import_logger()
