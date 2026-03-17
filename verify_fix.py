"""
Standalone verification script for PhaseZeroRecord program field fix.
Tests that the program ForeignKey on PhaseZeroRecord no longer allows blank values.

This script can be run without a database by checking model field properties
and form validation behavior.

Usage:
    Set VIRTUAL_ENV environment variable, then:
    python verify_fix.py
"""
import os
import sys
import platform

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esp.settings')
os.environ.setdefault('VIRTUAL_ENV', '/usr')

# Patch os.uname for Windows compatibility
if platform.system() == 'Windows':
    os.uname = lambda: ('Windows', platform.node(), platform.release(), platform.version(), platform.machine())

# Add the esp directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'esp'))

import django
django.setup()

from esp.program.models import PhaseZeroRecord, ModeratorRecord

def test_program_field_not_blank():
    """Test that PhaseZeroRecord.program does not have blank=True"""
    field = PhaseZeroRecord._meta.get_field('program')
    assert not field.blank, "FAIL: PhaseZeroRecord.program should not have blank=True"
    print("PASS: program field does not have blank=True")

def test_program_field_not_null():
    """Test that PhaseZeroRecord.program does not have null=True"""
    field = PhaseZeroRecord._meta.get_field('program')
    assert not field.null, "FAIL: PhaseZeroRecord.program should not have null=True"
    print("PASS: program field does not have null=True")

def test_program_field_has_cascade():
    """Test that PhaseZeroRecord.program uses CASCADE on_delete"""
    field = PhaseZeroRecord._meta.get_field('program')
    from django.db.models import CASCADE
    assert field.remote_field.on_delete == CASCADE, "FAIL: on_delete should be CASCADE"
    print("PASS: program field uses CASCADE on_delete")

def test_program_field_consistent_with_moderator():
    """Test that PhaseZeroRecord.program is now consistent with ModeratorRecord.program"""
    pzr_field = PhaseZeroRecord._meta.get_field('program')
    mr_field = ModeratorRecord._meta.get_field('program')
    assert pzr_field.blank == mr_field.blank, (
        "FAIL: PhaseZeroRecord.program.blank (%s) should match "
        "ModeratorRecord.program.blank (%s)" % (pzr_field.blank, mr_field.blank)
    )
    print("PASS: program field is consistent with ModeratorRecord.program")

def test_model_form_requires_program():
    """Test that a ModelForm for PhaseZeroRecord requires the program field"""
    from django.forms import ModelForm

    class PhaseZeroRecordForm(ModelForm):
        class Meta:
            model = PhaseZeroRecord
            fields = ['program']

    form = PhaseZeroRecordForm(data={})
    assert not form.is_valid(), "FAIL: Form should be invalid without program"
    assert 'program' in form.errors, "FAIL: 'program' should be in form errors"
    print("PASS: ModelForm requires program field")

def test_model_form_accepts_valid_program():
    """Test that a ModelForm for PhaseZeroRecord accepts a valid program id"""
    from django.forms import ModelForm

    class PhaseZeroRecordForm(ModelForm):
        class Meta:
            model = PhaseZeroRecord
            fields = ['program']

    # We can't test with a real program ID without a database,
    # but we can verify the form field is required
    form = PhaseZeroRecordForm(data={})
    assert form.fields['program'].required, "FAIL: program form field should be required"
    print("PASS: program form field is marked as required")

if __name__ == '__main__':
    print("=" * 60)
    print("PhaseZeroRecord Program Field Fix Verification")
    print("=" * 60)
    
    tests = [
        test_program_field_not_blank,
        test_program_field_not_null,
        test_program_field_has_cascade,
        test_program_field_consistent_with_moderator,
        test_model_form_requires_program,
        test_model_form_accepts_valid_program,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print("FAIL: %s - %s" % (test.__name__, str(e)))
            failed += 1
    
    print("=" * 60)
    print("Results: %d passed, %d failed" % (passed, failed))
    print("=" * 60)
    
    sys.exit(0 if failed == 0 else 1)
