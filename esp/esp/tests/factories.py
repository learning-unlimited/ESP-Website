"""
Test factories for the ESP test suite.

WHY THIS EXISTS
---------------
ProgramFrameworkTest is a full integration harness — it creates a complete
program with timeslots, rooms, teachers, students, and classes. That is
exactly what you want for integration tests.

But for unit tests (e.g. ClassCreationController, LotteryAssignmentController)
you often need just one user, or just one class, without spinning up an entire
program. The copy-paste pattern for doing this is scattered across 8+ test
files with no shared abstraction.

These factories provide the minimal building blocks:
  - make_user(role)                  — one ESPUser with the right Group
  - make_program(**kwargs)           — one Program with sensible defaults
  - make_class(program, teacher)     — one ClassSubject + ClassSection + category

They are intentionally thin wrappers around the same model calls that
ProgramFrameworkTest uses internally, so behaviour is consistent.

USAGE
-----
    from esp.tests.factories import make_user, make_program, make_class

    # In a CacheFlushTestCase or ProgramFrameworkTest subclass:
    teacher = make_user('Teacher')
    program = make_program()
    cls     = make_class(program, teacher)

ADDRESSES
---------
  Issue #3780 — Expand test coverage
  Issue #4480 — Improve test coverage properly
"""

import re
import unicodedata
from datetime import datetime, timedelta

from django.contrib.auth.models import Group

from esp.cal.models import Event, EventType
from esp.program.forms import ProgramCreationForm
from esp.program.models import (
    ClassCategories,
    ClassSubject,
    ProgramModule,
)
from esp.program.setup import commit_program, prepare_program
from esp.resources.models import Resource, ResourceType
from esp.tests.util import user_role_setup
from esp.users.models import ESPUser, Permission


# ---------------------------------------------------------------------------
# User factory
# ---------------------------------------------------------------------------

def make_user(role, username=None, password='password'):
    """Create and return a single ESPUser with the given role.

    This is the single-user equivalent of the user-creation loop inside
    ProgramFrameworkTest.setUp(). It uses get_or_create so it is safe to
    call multiple times in the same test session.

    Args:
        role (str):         The role Group name. Standard values used in ESP:
                            'Student', 'Teacher', 'Administrator',
                            'Educator', 'Guardian', 'Volunteer'.
        username (str):     Optional explicit username. If omitted, a name
                            is derived from the role (e.g. 'test_student').
        password (str):     Password to set. Defaults to 'password' to match
                            the convention used throughout the test suite.

    Returns:
        ESPUser: The created (or retrieved) user, with password set and
                 role Group membership established.

    Example:
        teacher = make_user('Teacher')
        admin   = make_user('Administrator', username='my_admin')
    """
    # Ensure the role Groups exist — same call as ProgramFrameworkTest
    user_role_setup()

    if username is None:
        username = 'test_%s' % role.lower()

    user, created = ESPUser.objects.get_or_create(
        username=username,
        defaults={
            'first_name': role,
            'last_name':  'TestUser',
            'email':      '%s@test.learningu.org' % username,
        }
    )
    user.set_password(password)
    user.save()
    user.makeRole(role)
    return user


# ---------------------------------------------------------------------------
# Program factory
# ---------------------------------------------------------------------------

def make_program(
    program_type='TestProgram',
    instance_name='2222_Summer',
    instance_label='Summer 2222',
    grade_min=7,
    grade_max=12,
    base_cost=0,
    num_timeslots=3,
    timeslot_length=50,
    timeslot_gap=10,
    num_rooms=2,
    room_capacity=30,
    admin=None,
):
    """Create and return a minimal Program suitable for unit tests.

    Mirrors the program-creation logic in ProgramFrameworkTest.setUp() so
    the resulting object behaves identically to programs used in integration
    tests.

    Args:
        program_type (str):    Program type string, used to build the URL slug.
        instance_name (str):   Term identifier, e.g. '2222_Summer'.
        instance_label (str):  Human-readable term label.
        grade_min (int):       Minimum grade for the program.
        grade_max (int):       Maximum grade for the program.
        base_cost (int):       Base registration cost.
        num_timeslots (int):   Number of time slots to create.
        timeslot_length (int): Length of each slot in minutes.
        timeslot_gap (int):    Gap between slots in minutes.
        num_rooms (int):       Number of classroom resources to create.
        room_capacity (int):   Capacity of each room.
        admin (ESPUser|None):  Admin user for the program. If None, one is
                               created automatically via make_user().

    Returns:
        Program: The created program, fully committed with permissions.

    Example:
        program = make_program()
        program = make_program(program_type='Splash', instance_name='2023_Fall')
    """
    user_role_setup()

    # Reset the ResourceType cache before creating resources.
    # Django TestCase resets the DB between tests but this class-level cache
    # persists, which can cause subsequent tests to reuse a cached
    # ResourceType whose DB row no longer exists and then fail FK inserts.
    # ProgramFrameworkTest.setUp() does the same reset explicitly.
    ResourceType._get_or_create_cache = {}

    if admin is None:
        admin = make_user('Administrator', username='factory_admin')

    # Build a default category so the program has at least one
    category, _ = ClassCategories.objects.get_or_create(
        category='Factory Category',
        defaults={'symbol': 'F'},
    )

    prog_form_values = {
        'term':              instance_name,
        'term_friendly':     instance_label,
        'grade_min':         str(grade_min),
        'grade_max':         str(grade_max),
        'director_email':    'factory@test.learningu.org',
        'program_size_max':  '3000',
        'program_type':      program_type,
        'program_modules':   ProgramModule.objects.all(),
        'class_categories':  [category.id],
        'admins':            [admin.id],
        'teacher_reg_start': '2000-01-01 00:00:00',
        'teacher_reg_end':   '3001-01-01 00:00:00',
        'student_reg_start': '2000-01-01 00:00:00',
        'student_reg_end':   '3001-01-01 00:00:00',
        'base_cost':         base_cost,
        'sibling_discount':  0,
    }

    pcf = ProgramCreationForm(prog_form_values)
    if not pcf.is_valid():
        raise ValueError(
            "make_program(): ProgramCreationForm is invalid: %s" % pcf.errors
        )

    temp_prog = pcf.save(commit=False)
    perms, modules = prepare_program(temp_prog, pcf.data)

    new_prog = pcf.save(commit=False)
    ptype_slug = re.sub(
        r'[-\s]+', '_',
        re.sub(
            r'[^\w\s-]', '',
            unicodedata.normalize('NFKD', pcf.cleaned_data['program_type'])
        ).strip()
    )
    new_prog.url  = ptype_slug + '/' + pcf.cleaned_data['term']
    new_prog.name = (
        pcf.cleaned_data['program_type'] + ' ' + pcf.cleaned_data['term_friendly']
    )
    new_prog.save()
    pcf.save_m2m()
    commit_program(
        new_prog, perms,
        pcf.cleaned_data['base_cost'],
        pcf.cleaned_data['sibling_discount'],
    )

    # Open registration for teachers and students — same as ProgramFrameworkTest
    Permission.objects.get_or_create(
        role=Group.objects.get(name='Teacher'),
        permission_type='Teacher/All',
        program=new_prog,
    )
    Permission.objects.get_or_create(
        role=Group.objects.get(name='Student'),
        permission_type='Student/All',
        program=new_prog,
    )

    # Create timeslots
    event_type = EventType.get_from_desc('Class Time Block')
    start_time = datetime(2222, 7, 7, 7, 5)
    for i in range(num_timeslots):
        slot_start = start_time + timedelta(
            minutes=i * (timeslot_length + timeslot_gap)
        )
        slot_end = slot_start + timedelta(minutes=timeslot_length)
        Event.objects.get_or_create(
            program=new_prog,
            event_type=event_type,
            start=slot_start,
            end=slot_end,
            short_description='Slot %d' % i,
            defaults={'description': slot_start.strftime('%H:%M %m/%d/%Y')},
        )

    # Create classroom resources.
    # Cache timeslots once (same pattern as ProgramFrameworkTest) to avoid
    # re-querying the DB once per room when num_rooms is large.
    timeslots = list(new_prog.getTimeSlots())
    for i in range(num_rooms):
        for ts in timeslots:
            Resource.objects.get_or_create(
                name='Room %d' % i,
                num_students=room_capacity,
                event=ts,
                res_type=ResourceType.get_or_create('Classroom'),
            )

    return new_prog


# ---------------------------------------------------------------------------
# Class factory
# ---------------------------------------------------------------------------

def make_class(program, teacher, title=None, category=None,
               grade_min=7, grade_max=12, class_size_max=30,
               duration=None, accept=False):
    """Create and return a ClassSubject with one ClassSection.

    Note: unlike ProgramFrameworkTest.setUp() which calls cls.accept() on
    every class it creates, this factory leaves the class unreviewed/unaccepted
    by default. Pass accept=True if your test requires an accepted class.

    Uses get_or_create so it is safe to call multiple times.

    Args:
        program (Program):          The program this class belongs to.
        teacher (ESPUser):          The teacher to assign to the class.
        title (str|None):           Class title. Auto-generated if None.
        category (ClassCategories|None):
                                    Category for the class. Uses the first
                                    category on the program if None.
        grade_min (int):            Minimum grade. Defaults to 7.
        grade_max (int):            Maximum grade. Defaults to 12.
        class_size_max (int):       Maximum class size. Defaults to 30.
        duration (float|None):      Section duration in hours. Derived from
                                    program timeslot length if None.
        accept (bool):              If True, call cls.accept() so the class
                                    starts in accepted/approved status.
                                    Defaults to False (unreviewed).

    Returns:
        ClassSubject: The created (or retrieved) class, with one section
                      added and the teacher assigned.

    Example:
        teacher = make_user('Teacher')
        program = make_program()
        cls     = make_class(program, teacher)
        cls     = make_class(program, teacher, title='Advanced Python', accept=True)
    """
    if title is None:
        title = 'Factory Class for %s' % teacher.username

    if category is None:
        # Use the first category associated with the program, or create one
        cats = program.class_categories.all()
        if cats.exists():
            category = cats.first()
        else:
            category, _ = ClassCategories.objects.get_or_create(
                category='Factory Category',
                defaults={'symbol': 'F'},
            )

    if duration is None:
        # Derive from program timeslot length — same logic as ProgramFrameworkTest
        durations = program.getDurations()
        duration = float(durations[0][0]) if durations else 1.0

    cls, created = ClassSubject.objects.get_or_create(
        title=title,
        parent_program=program,
        defaults={
            'category':       category,
            'grade_min':      grade_min,
            'grade_max':      grade_max,
            'class_size_max': class_size_max,
            'class_info':     'Auto-generated by make_class() factory.',
        },
    )

    cls.makeTeacher(teacher)

    # Add a section if none exists yet
    if cls.get_sections().count() == 0:
        cls.add_section(duration=duration)

    if accept:
        cls.accept()

    return cls
