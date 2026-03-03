#!/usr/bin/env python
"""Setup waitlist testing for Cascade 2026"""
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'esp.settings')

import django
django.setup()

from datetime import datetime, timedelta
from django.contrib.auth.models import Group
from esp.program.models import Program, ClassSubject, ClassSection, RegistrationType, ClassCategories, RegistrationProfile
from esp.program.modules.module_ext import StudentClassRegModuleInfo, ClassRegModuleInfo
from esp.users.models import ESPUser, Permission, StudentInfo
from esp.cal.models import Event, EventType

# Get program
p = Program.objects.get(url='Cascade/2026')
print(f'Program: {p.name}')

# 1. Enable waitlist settings
print('\n1. Enabling waitlist...')
reg_info, created = StudentClassRegModuleInfo.objects.get_or_create(
    program=p,
    defaults={
        'enable_class_waitlist': True,
        'max_waitlist_per_timeslot': 1,
        'register_from_catalog': True,
    }
)
if not created:
    reg_info.enable_class_waitlist = True
    reg_info.max_waitlist_per_timeslot = 1
    reg_info.register_from_catalog = True
    reg_info.save()
print('   Waitlist enabled!')

# 2. Create ClassRegModuleInfo if needed
class_reg, _ = ClassRegModuleInfo.objects.get_or_create(program=p)
print('   ClassRegModuleInfo ready!')

# 3. Get or create timeslot
print('\n2. Getting timeslot...')
timeslots = Event.objects.filter(program=p)
if timeslots.exists():
    timeslot = timeslots.first()
    print(f'   Using existing timeslot: {timeslot}')
else:
    timeslot_type = EventType.get_from_desc('Class Time Block')
    now = datetime.now()
    timeslot = Event.objects.create(
        program=p,
        short_description='Morning Block',
        description='Class Time',
        start=now,
        end=now + timedelta(hours=1),
        event_type=timeslot_type,
    )
    print(f'   Created timeslot: {timeslot}')

# 4. Create teacher
print('\n3. Creating teacher...')
teacher, created = ESPUser.objects.get_or_create(
    username='cascade_teacher',
    defaults={
        'email': 'cascade_teacher@example.com',
        'first_name': 'Cascade',
        'last_name': 'Teacher',
    }
)
if created:
    teacher.set_password('password')
    teacher.save()
teacher.makeRole('Teacher')
print(f'   Teacher: cascade_teacher / password')

# 5. Create category
print('\n4. Creating category...')
category, _ = ClassCategories.objects.get_or_create(
    category='Technology',
    defaults={'symbol': 'T'}
)
p.class_categories.add(category)
print(f'   Category: {category}')

# 6. Create the AI/ML class with CAPACITY 2
print('\n5. Creating class: Intro to AI/ML (capacity: 2)...')
cls, created = ClassSubject.objects.get_or_create(
    title='Intro to AI/ML',
    parent_program=p,
    defaults={
        'class_info': 'Learn the basics of Artificial Intelligence and Machine Learning',
        'category': category,
        'grade_min': 7,
        'grade_max': 12,
        'class_size_max': 2,
        'status': 10,
    }
)
if not created:
    cls.class_size_max = 2
    cls.status = 10
    cls.save()
cls.makeTeacher(teacher)
print(f'   Class created!')

# 7. Create section with capacity 2
section = cls.sections.first()
if not section:
    section = cls.add_section(duration=1.0)
section.max_class_capacity = 2
section.status = 10
section.registration_status = 0  # Open
section.save()
section.meeting_times.add(timeslot)
print(f'   Section created with capacity: 2')

# 8. Create 3 students
print('\n6. Creating 3 students...')
for i in range(1, 4):
    student, created = ESPUser.objects.get_or_create(
        username=f'cascade_student{i}',
        defaults={
            'email': f'cascade_student{i}@example.com',
            'first_name': 'Student',
            'last_name': f'{i}',
        }
    )
    if created:
        student.set_password('password')
        student.save()
    student.makeRole('Student')
    
    # Set grade 10
    graduation_year = ESPUser.YOGFromGrade(10)
    student_info, _ = StudentInfo.objects.get_or_create(
        user=student,
        defaults={'graduation_year': graduation_year}
    )
    student_info.graduation_year = graduation_year
    student_info.save()
    
    reg_profile, _ = RegistrationProfile.objects.get_or_create(
        user=student,
        most_recent_profile=True,
        defaults={'student_info': student_info}
    )
    reg_profile.student_info = student_info
    reg_profile.save()
    
    print(f'   cascade_student{i} / password (grade 10)')

# 9. Set permissions
print('\n7. Setting permissions...')
student_role = Group.objects.get(name='Student')
now = datetime.now()
future = now + timedelta(days=365)

for perm_type in ['Student', 'Student/Classes', 'Student/Classes/Waitlist']:
    perm, created = Permission.objects.get_or_create(
        permission_type=perm_type,
        program=p,
        role=student_role,
        defaults={
            'start_date': now - timedelta(days=1),
            'end_date': future,
        }
    )
    if not created:
        perm.start_date = now - timedelta(days=1)
        perm.end_date = future
        perm.save()
    print(f'   {perm_type}: OK')

# 10. Ensure Waitlisted registration type exists
RegistrationType.objects.get_or_create(name='Waitlisted', defaults={'category': 'student'})
RegistrationType.objects.get_or_create(name='Enrolled', defaults={'category': 'student'})
print('   Registration types: OK')

print()
print('='*60)
print('SETUP COMPLETE!')
print('='*60)
print('''
Program: Cascade 2026
Catalog: http://localhost:8000/learn/Cascade/2026/catalog

CLASS: Intro to AI/ML
  Capacity: 2 students (waitlist activates after 2 enroll)

STUDENTS:
  cascade_student1 / password
  cascade_student2 / password  
  cascade_student3 / password

TO TEST WAITLIST:
  1. Login as cascade_student1, enroll in "Intro to AI/ML"
  2. Login as cascade_student2, enroll in same class (NOW FULL)
  3. Login as cascade_student3, try to enroll -> see "Join Waitlist"
  4. Click "Join Waitlist"
  5. Login as cascade_student1, drop the class
  6. cascade_student3 should be auto-promoted!
''')
