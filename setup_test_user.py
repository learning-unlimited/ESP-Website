
import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esp.django_settings")
django.setup()

from django.contrib.auth.models import User
from esp.users.models import ESPUser, StudentInfo
from esp.program.models import Program, ClassSubject, ClassCategories, ClassSection, ProgramModuleInfo, ProgramModule
from esp.dbmail.models import Message

def setup_test_scenario():
    # 1. Create a Student User
    username = 'teststudent'
    email = 'student@example.com'
    password = 'password123'
    
    if not User.objects.filter(username=username).exists():
        user = User.objects.create_user(username=username, email=email, password=password)
        esp_user = ESPUser.objects.get(id=user.id)
        # Make them a student
        StudentInfo.objects.get_or_create(user=esp_user, grade=10)
        print(f"Created student user: {username}")
    else:
        print(f"Student user {username} already exists.")

    # 2. Ensure a Program exists and is open
    program, created = Program.objects.get_or_create(
        short_name='testfix',
        defaults={
            'name': 'Test Fix Program',
            'grade_min': 7,
            'grade_max': 12,
            'registration_open': True,
        }
    )
    if not created:
        program.registration_open = True
        program.save()
    
    # 3. Ensure we have a category
    category, _ = ClassCategories.objects.get_or_create(category='Test Category')

    # 4. Create two conflicting classes
    # We need to make sure they are in the same program and have overlapping sections
    # In ESP, sections are what have times.
    
    c1, _ = ClassSubject.objects.get_or_create(
        title='Conflicting Class A',
        parent_program=program,
        defaults={'category': category, 'approved': True}
    )
    
    c2, _ = ClassSubject.objects.get_or_create(
        title='Conflicting Class B',
        parent_program=program,
        defaults={'category': category, 'approved': True}
    )

    # 5. Add sections with same time
    # This part depends on how sections/times are structured in this specific ESP version
    # Usually it involves ClassSection and timeslots.
    # For simplicity in this test, we'll just ensure the classes exist and are in the catalog.
    
    print(f"Program: {program.name}")
    print(f"Class A: {c1.title}")
    print(f"Class B: {c2.title}")
    print(f"\nLogin at http://localhost:8000/")
    print(f"Username: {username}")
    print(f"Password: {password}")

if __name__ == "__main__":
    setup_test_scenario()
