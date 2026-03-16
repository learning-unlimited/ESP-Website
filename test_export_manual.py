"""
Manual test for export_questions functionality.
This script verifies that the export_questions method works correctly.
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'esp'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esp.django_settings')
django.setup()

from django.contrib.auth.models import User, Group
from django.test import RequestFactory
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware

from esp.program.models import Program
from esp.survey.models import Survey, QuestionType, Question
from esp.survey.admin import SurveyAdmin


def setup_roles():
    """Create required user roles."""
    for name in ['Student', 'Teacher', 'Educator', 'Guardian', 'Volunteer', 'Administrator']:
        Group.objects.get_or_create(name=name)


def test_export_questions():
    """Test the export_questions functionality."""
    print("Setting up test data...")
    
    # Setup roles
    setup_roles()
    
    # Create test user
    user, _ = User.objects.get_or_create(
        username='test_admin',
        defaults={
            'email': 'admin@test.com',
            'is_superuser': True,
            'is_staff': True
        }
    )
    user.set_password('password')
    user.save()
    
    # Create test program and survey
    program, _ = Program.objects.get_or_create(
        grade_min=7,
        grade_max=12
    )
    
    survey, _ = Survey.objects.get_or_create(
        name='Export Test Survey',
        defaults={
            'program': program,
            'category': 'learn',
        }
    )
    
    # Create question types
    qt_yesno, _ = QuestionType.objects.get_or_create(
        name='Yes/No',
        defaults={
            '_param_names': '',
            'is_numeric': False,
            'is_countable': False,
        }
    )
    
    qt_rating, _ = QuestionType.objects.get_or_create(
        name='Rating',
        defaults={
            '_param_names': 'min|max',
            'is_numeric': True,
            'is_countable': True,
        }
    )
    
    # Clear existing questions for this survey
    Question.objects.filter(survey=survey).delete()
    
    # Create test questions
    print("Creating test questions...")
    q1 = Question.objects.create(
        survey=survey,
        name='Did you enjoy the program?',
        question_type=qt_yesno,
        _param_values='',
        per_class=False,
        seq=1
    )
    
    q2 = Question.objects.create(
        survey=survey,
        name='Rate the program',
        question_type=qt_rating,
        _param_values='1|5',
        per_class=False,
        seq=2
    )
    
    print(f"Created {Question.objects.filter(survey=survey).count()} questions")
    
    # Setup admin
    site = AdminSite()
    admin = SurveyAdmin(Survey, site)
    factory = RequestFactory()
    
    # Create request
    request = factory.get('/admin/survey/survey/')
    request.user = user
    
    # Add session
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    
    # Add messages
    setattr(request, '_messages', FallbackStorage(request))
    
    # Test export
    print("\nTesting export_questions...")
    queryset = Survey.objects.filter(id=survey.id)
    response = admin.export_questions(request, queryset)
    
    # Verify response
    print(f"Response status code: {response.status_code}")
    print(f"Content-Type: {response['Content-Type']}")
    print(f"Content-Disposition: {response['Content-Disposition']}")
    
    # Verify CSV content
    content = response.content.decode('utf-8')
    lines = content.strip().split('\n')
    
    print(f"\nCSV has {len(lines)} lines (including header)")
    print("\nCSV Content:")
    print("-" * 80)
    for i, line in enumerate(lines, 1):
        print(f"Line {i}: {line}")
    print("-" * 80)
    
    # Verify expectations
    assert response.status_code == 200, "Response should be 200 OK"
    assert response['Content-Type'] == 'text/csv', "Content-Type should be text/csv"
    assert 'attachment' in response['Content-Disposition'], "Should be an attachment"
    assert len(lines) == 3, f"Should have 3 lines (header + 2 questions), got {len(lines)}"
    assert 'question_name' in lines[0], "Header should contain question_name"
    assert 'Did you enjoy the program?' in lines[1], "First question should be in CSV"
    assert 'Rate the program' in lines[2], "Second question should be in CSV"
    assert '1|5' in lines[2], "Rating parameters should be in CSV"
    
    print("\n✓ All assertions passed!")
    print("\nExport functionality is working correctly!")
    
    # Cleanup
    print("\nCleaning up test data...")
    Question.objects.filter(survey=survey).delete()
    survey.delete()
    program.delete()
    user.delete()
    
    print("✓ Cleanup complete!")


if __name__ == '__main__':
    try:
        test_export_questions()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
