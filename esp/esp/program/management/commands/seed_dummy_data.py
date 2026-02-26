"""
Comprehensive Django management command to seed the database with consistent
dummy data for local development.

- Uses Faker with a fixed seed for reproducibility across all dev environments.
- Fully idempotent: safe to run multiple times; existing records are skipped.
- Use --flush to wipe seeded data and start fresh.

Covers:
  django_site, auth groups
  users: ESPUser, ContactInfo, StudentInfo, TeacherInfo, GuardianInfo,
         K12School, UserAvailability, Record, RecordType, Permission
  program: Program, ProgramModule, ClassCategories, ClassSubject, ClassSection,
           TeacherBio, RegistrationProfile, RegistrationType,
           StudentRegistration, VolunteerRequest, VolunteerOffer, SplashInfo
  cal: EventType, Event
  resources: ResourceType, Resource, ResourceAssignment
  qsd: NavBarCategory, NavBarEntry, QuasiStaticData
  survey: QuestionType, Survey, Question, SurveyResponse, Answer
  tags: Tag
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.db import transaction
from django.utils import timezone
from faker import Faker
import random
from datetime import datetime, timedelta

from esp.program.models import (
    Program, RegistrationType, StudentRegistration,
    VolunteerRequest, VolunteerOffer, RegistrationProfile,
    TeacherBio, ProgramModule, SplashInfo,
)
from esp.program.models.class_ import ClassSubject, ClassSection, ClassCategories
from esp.program.modules.module_ext import ClassRegModuleInfo, StudentClassRegModuleInfo
from esp.cal.models import Event, EventType
from esp.resources.models import Resource, ResourceType, ResourceAssignment
from esp.users.models import (
    ESPUser, StudentInfo, TeacherInfo, GuardianInfo,
    ContactInfo, UserAvailability, K12School, Record, RecordType,
    Permission as ESPPermission,
)
from esp.web.models import NavBarCategory, NavBarEntry
from esp.qsd.models import QuasiStaticData
from esp.survey.models import Survey, SurveyResponse, Question, Answer, QuestionType
from esp.tagdict.models import Tag


SEED_USERNAMES = (
    ['admin'] +
    [f'teacher{i}' for i in range(1, 6)] +
    [f'student{i}' for i in range(1, 16)] +
    [f'volunteer{i}' for i in range(1, 4)]
)
SEED_PROGRAM_URLS = ['SplashDev/2026', 'SparkDev/2026']


class Command(BaseCommand):
    help = 'Seeds the database with consistent dummy data for local development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush', action='store_true',
            help='Clear existing seeded data before creating new data',
        )

    def handle(self, *args, **options):
        Faker.seed(42)
        random.seed(42)
        self.fake = Faker('en_US')

        if options['flush']:
            self.stdout.write('Flushing existing seed data...')
            self.flush_seeded_data()

        self.stdout.write('Starting database seeding...')

        with transaction.atomic():
            self._seed_site()
            self._seed_groups()
            self._seed_lookup_data()
            self._seed_navbar()

            admin = self._create_admin()
            school = self._create_school(admin)
            programs = self._create_programs()
            self._create_global_qsd(admin, programs[0].name)

            for program in programs:
                self.stdout.write(f'  Seeding program: {program.name}')
                timeslots  = self._create_timeslots(program)
                classrooms = self._create_classrooms(program, timeslots)
                teachers, sections = self._create_teachers(program, timeslots, classrooms)
                self._backfill_section_durations(program)
                students = self._create_students(program, sections, school)
                self._create_volunteers(program, timeslots)
                self._create_survey(program, teachers)
                self._create_tags(program)
                self._create_qsd(program, admin)
                self._create_splash_info(program, students)

        self.stdout.write(self.style.SUCCESS('✓ Database seeding completed successfully!'))
        self.stdout.write('Admin credentials: username=admin  password=password')

    # ── flush ─────────────────────────────────────────────────────────────────

    def flush_seeded_data(self):
        from django.db import connection

        program_ids = list(
            Program.objects.filter(url__in=SEED_PROGRAM_URLS).values_list('id', flat=True)
        )
        if not program_ids:
            self.stdout.write('  Nothing to flush.')
            return

        ids_sql = '(' + ','.join(str(i) for i in program_ids) + ')'

        with connection.cursor() as cursor:
            # Delete in dependency order using raw SQL to bypass
            # the "unhashable type: ClassSubject" bug in ClassSubject.delete()

            # Student registrations -> sections -> subjects
            cursor.execute(f"""
                DELETE FROM program_studentregistration
                WHERE section_id IN (
                    SELECT cs.id FROM program_classsection cs
                    JOIN program_class c ON cs.parent_class_id = c.id
                    WHERE c.parent_program_id IN {ids_sql}
                )
            """)
            cursor.execute(f"""
                DELETE FROM program_classsection_meeting_times
                WHERE classsection_id IN (
                    SELECT cs.id FROM program_classsection cs
                    JOIN program_class c ON cs.parent_class_id = c.id
                    WHERE c.parent_program_id IN {ids_sql}
                )
            """)
            cursor.execute(f"""
                DELETE FROM resources_resourceassignment
                WHERE target_id IN (
                    SELECT cs.id FROM program_classsection cs
                    JOIN program_class c ON cs.parent_class_id = c.id
                    WHERE c.parent_program_id IN {ids_sql}
                )
            """)
            cursor.execute(f"""
                DELETE FROM program_classsection
                WHERE parent_class_id IN (
                    SELECT id FROM program_class WHERE parent_program_id IN {ids_sql}
                )
            """)
            cursor.execute(f"DELETE FROM program_class_meeting_times WHERE classsubject_id IN (SELECT id FROM program_class WHERE parent_program_id IN {ids_sql})")
            cursor.execute(f"DELETE FROM program_class_teachers WHERE classsubject_id IN (SELECT id FROM program_class WHERE parent_program_id IN {ids_sql})")
            cursor.execute(f"DELETE FROM program_class WHERE parent_program_id IN {ids_sql}")

            # Other program-related tables
            cursor.execute(f"DELETE FROM program_volunteeroffer WHERE request_id IN (SELECT id FROM program_volunteerrequest WHERE program_id IN {ids_sql})")
            cursor.execute(f"DELETE FROM program_volunteerrequest WHERE program_id IN {ids_sql}")
            cursor.execute(f"DELETE FROM program_registrationprofile WHERE program_id IN {ids_sql}")
            cursor.execute(f"DELETE FROM program_teacherbio WHERE program_id IN {ids_sql}")

            # users_useravailability references cal_event via event_id
            cursor.execute(f"""
                DELETE FROM users_useravailability
                WHERE event_id IN (SELECT id FROM cal_event WHERE program_id IN {ids_sql})
            """)
            # resources_resourceassignment also references resources_resource via resource_id
            cursor.execute(f"""
                DELETE FROM resources_resourceassignment
                WHERE resource_id IN (
                    SELECT id FROM resources_resource
                    WHERE event_id IN (SELECT id FROM cal_event WHERE program_id IN {ids_sql})
                )
            """)
            # resources_resource references cal_event via event_id
            cursor.execute(f"""
                DELETE FROM resources_resource
                WHERE event_id IN (SELECT id FROM cal_event WHERE program_id IN {ids_sql})
            """)
            cursor.execute(f"DELETE FROM cal_event WHERE program_id IN {ids_sql}")

            # Survey tables reference program_program; delete in FK order
            cursor.execute(f"""
                DELETE FROM survey_answer
                WHERE survey_response_id IN (
                    SELECT id FROM survey_surveyresponse
                    WHERE survey_id IN (SELECT id FROM survey_survey WHERE program_id IN {ids_sql})
                )
            """)
            cursor.execute(f"""
                DELETE FROM survey_surveyresponse
                WHERE survey_id IN (SELECT id FROM survey_survey WHERE program_id IN {ids_sql})
            """)
            cursor.execute(f"""
                DELETE FROM survey_question
                WHERE survey_id IN (SELECT id FROM survey_survey WHERE program_id IN {ids_sql})
            """)
            cursor.execute(f"DELETE FROM survey_survey WHERE program_id IN {ids_sql}")

            # All modules_* tables that hold a FK to program_program
            cursor.execute(f"""
                DELETE FROM modules_ajaxchangelog_entries
                WHERE ajaxchangelog_id IN (
                    SELECT id FROM modules_ajaxchangelog WHERE program_id IN {ids_sql}
                )
            """)
            cursor.execute(f"DELETE FROM modules_ajaxchangelog WHERE program_id IN {ids_sql}")
            cursor.execute(f"DELETE FROM modules_ajaxsectiondetail WHERE program_id IN {ids_sql}")
            cursor.execute(f"DELETE FROM modules_studentclassregmoduleinfo WHERE program_id IN {ids_sql}")
            cursor.execute(f"DELETE FROM modules_classregmoduleinfo WHERE program_id IN {ids_sql}")
            cursor.execute(f"DELETE FROM modules_dbreceipt WHERE program_id IN {ids_sql}")
            cursor.execute(f"DELETE FROM modules_programmoduleobj WHERE program_id IN {ids_sql}")

            # users_permission and users_record hold a FK to program_program
            cursor.execute(f"DELETE FROM users_permission WHERE program_id IN {ids_sql}")
            cursor.execute(f"DELETE FROM users_record WHERE program_id IN {ids_sql}")

            cursor.execute(f"DELETE FROM program_program_program_modules WHERE program_id IN {ids_sql}")
            cursor.execute(f"DELETE FROM program_program_class_categories WHERE program_id IN {ids_sql}")
            cursor.execute(f"DELETE FROM program_splashinfo WHERE program_id IN {ids_sql}")
            cursor.execute(f"DELETE FROM program_program WHERE id IN {ids_sql}")

        from django.db.models import Q
        qsd_filter = Q(url='index') | Q(url='faq') | Q(url='contact')
        qsd_filter |= Q(url='learn/index') | Q(url='teach/index') | Q(url='volunteer/index')
        for prog_url in SEED_PROGRAM_URLS:
            qsd_filter |= Q(url__contains=prog_url)
        QuasiStaticData.objects.filter(qsd_filter).delete()

        K12School.objects.filter(name='Dev High School').delete()
        Tag.objects.filter(key='seeded_data').delete()
        NavBarCategory.objects.filter(name='Dev Navbar').delete()
        for username in SEED_USERNAMES:
            ESPUser.objects.filter(username=username).delete()

    # ── site & groups ─────────────────────────────────────────────────────────

    def _seed_site(self):
        site, _ = Site.objects.get_or_create(id=1, defaults=dict(
            domain='devsite.learningu.org', name='LU Dev Site'))
        site.domain = 'devsite.learningu.org'
        site.name = 'LU Dev Site'
        site.save()

    def _seed_groups(self):
        for name in ['Student', 'Teacher', 'Guardian', 'Educator',
                     'Volunteer', 'Administrator', 'StudentRep']:
            Group.objects.get_or_create(name=name)

    # ── lookup / reference data ───────────────────────────────────────────────

    def _seed_lookup_data(self):
        for desc in ['Class Time Block', 'Open Block', 'Lunch', 'Setup', 'Teardown']:
            EventType.objects.get_or_create(description=desc)

        for name, desc in [
            ('Classroom',    'A standard classroom'),
            ('Projector',    'LCD projector'),
            ('Whiteboard',   'Whiteboard in room'),
            ('Computer Lab', 'Room with computers'),
        ]:
            ResourceType.objects.get_or_create(name=name, defaults=dict(
                description=desc, consumable=False, priority_default=0,
                only_one=False, attributes_dumped='[]', autocreated=False, hidden=False))

        for symbol, category, seq in [
            ('M', 'Mathematics', 1), ('S', 'Science', 2),
            ('H', 'Humanities', 3), ('A', 'Arts', 4),
            ('C', 'Computer Science', 5), ('E', 'Engineering', 6),
            ('X', 'Miscellaneous', 7),
        ]:
            ClassCategories.objects.get_or_create(symbol=symbol,
                defaults=dict(category=category, seq=seq))

        for name, category in [
            ('Enrolled', 'student'), ('Waitlisted', 'student'),
            ('Rejected', 'student'), ('Teaching', 'teacher'),
        ]:
            RegistrationType.objects.get_or_create(name=name, category=category,
                defaults=dict(description=f'{name} registration'))

        for name, desc in [
            ('reg_confirmed',        'Student confirmed registration'),
            ('attended',             'Student attended program'),
            ('teacher_checked_in',   'Teacher checked in'),
            ('volunteer_checked_in', 'Volunteer checked in'),
        ]:
            RecordType.objects.get_or_create(name=name, defaults=dict(description=desc))

        for handler, admin_title, module_type, seq, required in [
            # Core modules (main entry-point views)
            ('StudentRegCore',        'Core Student Registration',  'learn',      -9999, False),
            ('TeacherRegCore',        'Core Teacher Registration',  'teach',      -9999, False),
            ('AdminCore',             'Program Dashboard',          'manage',     -9999, False),
            ('OnsiteCore',            'Onsite Reg Core Module',     'onsite',     -1000, False),
            ('VolunteerSignup',       'Volunteer Sign-up Module',   'volunteer',      0, False),
            # Registration & profile modules
            ('StudentClassRegModule', 'Student Class Registration', 'learn',         10, True),
            ('TeacherClassRegModule', 'Teacher Class Registration', 'teach',         10, False),
            ('AvailabilityModule',    'Teacher Availability',       'teach',          1, True),
            ('TeacherBioModule',      'Teacher Biography Editor',   'teach',       -111, False),
            # Management modules
            ('ResourceModule',        'Resource Management',        'manage',    -99999, False),
            ('VolunteerManage',       'Volunteer Management',       'manage',         0, False),
            ('SurveyManagement',      'Survey Management',          'manage',        25, False),
            ('ProgramPrintables',     'Program Printables',         'manage',         5, False),
            ('AdminVitals',           'Program Vitals',             'manage',        -2, False),
            # JSON data (needed by scheduling, catalog, etc.)
            ('JSONDataModule',        'JSON Data Module',           'json',           0, False),
        ]:
            ProgramModule.objects.get_or_create(
                handler=handler, module_type=module_type,
                defaults=dict(admin_title=admin_title, seq=seq,
                              required=required, choosable=1))

        # RegProfileModule has two variants (learn + teach) with the same handler
        ProgramModule.objects.get_or_create(
            handler='RegProfileModule', module_type='learn',
            defaults=dict(admin_title='Student Profile Editor',
                          seq=0, required=True, choosable=1))
        ProgramModule.objects.get_or_create(
            handler='RegProfileModule', module_type='teach',
            defaults=dict(admin_title='Teacher Profile Editor',
                          seq=0, required=True, choosable=1))

        for name in ['yes/no', 'rating', 'open response', 'multiple choice']:
            QuestionType.objects.get_or_create(name=name)

    # ── navbar ────────────────────────────────────────────────────────────────

    def _seed_navbar(self):
        cat, _ = NavBarCategory.objects.get_or_create(name='Dev Navbar', defaults=dict(
            path='/', include_auto_links=True, long_explanation='Dev nav'))
        for rank, text, link in [
            (1, 'Home', '/'), (2, 'Programs', '/learn/'),
            (3, 'Teach', '/teach/'), (4, 'Volunteer', '/volunteer/'),
        ]:
            NavBarEntry.objects.get_or_create(category=cat, text=text,
                defaults=dict(sort_rank=rank, link=link, indent=False))

    # ── admin ─────────────────────────────────────────────────────────────────

    def _create_admin(self):
        user, created = ESPUser.objects.get_or_create(username='admin', defaults=dict(
            email='admin@example.com', first_name='Admin', last_name='User',
            is_staff=True, is_superuser=True))
        if created:
            user.set_password('password')
            user.save()
            user.makeRole('Administrator')
            self._make_contact(user, 'Admin', 'User')
        return user

    # ── school ────────────────────────────────────────────────────────────────

    def _create_school(self, admin):
        school, created = K12School.objects.get_or_create(
            name='Dev High School',
            defaults=dict(school_type='Public', grades='7-12'))
        if created:
            contact, _ = ContactInfo.objects.get_or_create(
                user=admin, first_name='School', last_name='Office',
                defaults=dict(e_mail='office@devhighschool.edu', phone_day='555-0100',
                              address_country='US', receive_txt_message=False,
                              undeliverable=False))
            school.contact = contact
            school.save()
        return school

    # ── programs ──────────────────────────────────────────────────────────────

    def _create_programs(self):
        all_module_handlers = [
            'StudentRegCore', 'TeacherRegCore', 'AdminCore',
            'OnsiteCore', 'VolunteerSignup',
            'RegProfileModule',
            'StudentClassRegModule', 'TeacherClassRegModule',
            'AvailabilityModule', 'TeacherBioModule',
            'ResourceModule', 'VolunteerManage',
            'SurveyManagement', 'ProgramPrintables',
            'AdminVitals', 'JSONDataModule',
        ]
        programs = []
        for spec in [
            dict(name='Splash Dev', url='SplashDev/2026', grade_min=7,  grade_max=12),
            dict(name='Spark Dev',  url='SparkDev/2026',  grade_min=9,  grade_max=12),
        ]:
            program, created = Program.objects.get_or_create(
                url=spec['url'],
                defaults=dict(
                    name=spec['name'], grade_min=spec['grade_min'],
                    grade_max=spec['grade_max'],
                    director_email='director@example.com',
                    director_cc_email='', director_confidential_email='',
                    program_size_max=200, program_allow_waitlist=True,
                ))
            if created:
                program.class_categories.set(ClassCategories.objects.all())
                program.program_modules.set(
                    ProgramModule.objects.filter(handler__in=all_module_handlers))

                StudentClassRegModuleInfo.objects.get_or_create(
                    program=program, defaults=dict(
                        enforce_max=True, use_priority=False,
                        priority_limit=3, visible_enrollments=True,
                        visible_meeting_times=True,
                        register_from_catalog=False,
                        force_show_required_modules=False,
                    ))
                ClassRegModuleInfo.objects.get_or_create(
                    program=program, defaults=dict(
                        allow_coteach=True, set_prereqs=True,
                        class_max_duration=120, class_min_cap=5,
                        class_max_size=40, class_size_step=5,
                        num_teacher_questions=1, allowed_sections='1,2',
                        session_counts='1',
                    ))
            programs.append(program)
        return programs

    # ── timeslots ─────────────────────────────────────────────────────────────

    def _create_timeslots(self, program):
        et = EventType.objects.get(description='Class Time Block')
        base = datetime(2026, 3, 21, 9, 0)
        slots = []
        for i in range(5):
            start = base + timedelta(hours=i)
            event, _ = Event.objects.get_or_create(
                program=program, name=f'Timeslot {i+1}',
                defaults=dict(event_type=et, start=start,
                              end=start + timedelta(hours=1),
                              short_description=f'Block {i+1}',
                              description=f'Block {i+1} for {program.name}'))
            slots.append(event)
        return slots

    # ── classrooms ────────────────────────────────────────────────────────────

    def _create_classrooms(self, program, timeslots):
        ct = ResourceType.objects.get(name='Classroom')
        prefix = 100 if 'Splash' in program.name else 200
        rooms = []
        for slot in timeslots:
            for i in range(5):
                res, _ = Resource.objects.get_or_create(
                    name=f'Room {prefix + i + 1}', event=slot,
                    defaults=dict(res_type=ct, num_students=random.randint(20, 40)))
                rooms.append(res)
        return rooms

    # ── teachers ──────────────────────────────────────────────────────────────

    def _create_teachers(self, program, timeslots, classrooms):
        tgroup = Group.objects.get(name='Teacher')
        cats = list(ClassCategories.objects.all())
        teachers, sections = [], []

        for i in range(1, 6):
            username = f'teacher{i}'
            first = self.fake.first_name()
            last  = self.fake.last_name()

            user, created = ESPUser.objects.get_or_create(username=username,
                defaults=dict(email=f'{username}@example.com',
                              first_name=first, last_name=last))
            if created:
                user.set_password('password')
                user.save()
                user.makeRole('Teacher')

            ti, _ = TeacherInfo.objects.get_or_create(user=user, defaults=dict(
                graduation_year=str(random.randint(2010, 2024)),
                college=self.fake.company(), affiliation=self.fake.company(),
                major=random.choice(['CS', 'Math', 'Physics', 'Biology', 'English']),
                bio=self.fake.text(max_nb_chars=200)))

            contact = self._make_contact(user, user.first_name, user.last_name)

            TeacherBio.objects.get_or_create(user=user, program=program, defaults=dict(
                bio=self.fake.text(max_nb_chars=300),
                last_ts=timezone.now(), hidden=False))

            avail = random.sample(timeslots, random.randint(3, 5))
            for slot in avail:
                UserAvailability.objects.get_or_create(
                    user=user, event=slot, defaults=dict(role=tgroup))

            for _ in range(random.randint(1, 2)):
                cat   = random.choice(cats)
                slot  = random.choice(avail)
                title = f'{self.fake.catch_phrase()} - {cat.category}'

                subj, sc = ClassSubject.objects.get_or_create(
                    parent_program=program, title=title,
                    defaults=dict(category=cat, class_info=self.fake.text(max_nb_chars=500),
                                  grade_min=program.grade_min, grade_max=program.grade_max,
                                  class_size_max=30, status=10, allow_lateness=False,
                                  message_for_directors='', session_count=1, duration=1.0))
                if sc:
                    subj.teachers.add(user)
                    subj.meeting_times.add(slot)

                sec, secc = ClassSection.objects.get_or_create(
                    parent_class=subj,
                    defaults=dict(status=10, registration_status=0,
                                  duration=1.0,
                                  max_class_capacity=random.randint(20, 30),
                                  enrolled_students=0, attending_students=0))
                if secc:
                    sec.meeting_times.add(slot)
                    cands = [r for r in classrooms if r.event == slot]
                    if cands:
                        room = random.choice(cands)
                        ResourceAssignment.objects.get_or_create(
                            resource=room, target=sec)
                        classrooms.remove(room)

                sections.append(sec)

            self._make_reg_profile(user, program, contact_user=contact, teacher_info=ti)

            ESPPermission.objects.get_or_create(
                user=user, program=program, permission_type='Teacher',
                defaults=dict(start_date=timezone.now(),
                              end_date=timezone.now() + timedelta(days=365)))
            teachers.append(user)

        return teachers, sections

    def _backfill_section_durations(self, program):
        """Set duration=1.0 on any ClassSection with null duration (fixes getTaughtTime)."""
        ClassSection.objects.filter(
            parent_class__parent_program=program,
            duration__isnull=True,
        ).update(duration=1.0)

    # ── students ──────────────────────────────────────────────────────────────

    def _create_students(self, program, sections, school):
        enrolled_type   = RegistrationType.objects.get(name='Enrolled', category='student')
        confirmed_rtype = RecordType.objects.get(name='reg_confirmed')
        students = []

        for i in range(1, 16):
            username = f'student{i}'
            first = self.fake.first_name()
            last  = self.fake.last_name()

            user, created = ESPUser.objects.get_or_create(username=username,
                defaults=dict(email=f'{username}@example.com',
                              first_name=first, last_name=last))
            if created:
                user.set_password('password')
                user.save()
                user.makeRole('Student')

            grade = random.randint(program.grade_min, program.grade_max)
            dob   = datetime(2026 - grade - 6, random.randint(1, 12), random.randint(1, 28))

            si, _ = StudentInfo.objects.get_or_create(user=user, defaults=dict(
                graduation_year=2026 + (12 - grade), k12school=school,
                dob=dob, gender=random.choice(['Male', 'Female', 'Other/Prefer not to say']),
                studentrep=False, post_hs='', transportation='',
                schoolsystem_optout=False))

            cu  = self._make_contact(user, first, last)
            cg  = self._make_contact(user, self.fake.first_name(), last)
            ce  = self._make_contact(user, self.fake.first_name(), self.fake.last_name())

            gi, _ = GuardianInfo.objects.get_or_create(user=user, defaults=dict(
                num_kids=random.randint(1, 3), year_finished=random.randint(1980, 2000)))

            self._make_reg_profile(user, program, contact_user=cu,
                contact_guardian=cg, contact_emergency=ce,
                student_info=si, guardian_info=gi)

            for sec in random.sample(sections, random.randint(2, min(3, len(sections)))):
                StudentRegistration.objects.get_or_create(
                    user=user, section=sec, relationship=enrolled_type)

            Record.objects.get_or_create(user=user, program=program, event=confirmed_rtype)

            ESPPermission.objects.get_or_create(
                user=user, program=program, permission_type='Student',
                defaults=dict(start_date=timezone.now(),
                              end_date=timezone.now() + timedelta(days=365)))
            students.append(user)

        return students

    # ── volunteers ────────────────────────────────────────────────────────────

    def _create_volunteers(self, program, timeslots):
        volunteers = []
        for i in range(1, 4):
            username = f'volunteer{i}'
            user, created = ESPUser.objects.get_or_create(username=username,
                defaults=dict(email=f'{username}@example.com',
                              first_name=self.fake.first_name(),
                              last_name=self.fake.last_name()))
            if created:
                user.set_password('password')
                user.save()
                user.makeRole('Volunteer')
            contact = self._make_contact(user, user.first_name, user.last_name)
            self._make_reg_profile(user, program, contact_user=contact)
            volunteers.append(user)

        for slot in timeslots:
            req, _ = VolunteerRequest.objects.get_or_create(
                program=program, timeslot=slot, defaults=dict(num_volunteers=2))
            for vol in random.sample(volunteers, random.randint(1, 2)):
                VolunteerOffer.objects.get_or_create(
                    request=req, user=vol, defaults=dict(confirmed=True))

    # ── survey ────────────────────────────────────────────────────────────────

    def _create_survey(self, program, teachers):
        survey, survey_created = Survey.objects.get_or_create(
            name=f'Dev Survey - {program.name}', program=program,
            defaults=dict(category='learn'))

        rt = QuestionType.objects.get(name='rating')
        ot = QuestionType.objects.get(name='open response')

        # Question has: survey, name, question_type (FK), seq, per_class
        # There is no 'question' text field — the name IS the question label.
        q1, _ = Question.objects.get_or_create(survey=survey, name='Overall rating',
            defaults=dict(seq=1, question_type=rt))
        q2, _ = Question.objects.get_or_create(survey=survey, name='Feedback',
            defaults=dict(seq=2, question_type=ot))

        # SurveyResponse has no user field; only create responses when the
        # survey itself is new to keep the seeder idempotent.
        # Answer stores text via the 'answer' property (drives value/value_type).
        if survey_created:
            for _ in teachers[:3]:
                resp = SurveyResponse.objects.create(
                    survey=survey, time_filled=timezone.now())
                ans1 = Answer(question=q1, survey_response=resp)
                ans1.answer = str(random.randint(3, 5))
                ans1.save()
                ans2 = Answer(question=q2, survey_response=resp)
                ans2.answer = self.fake.sentence()
                ans2.save()

    # ── tags ─────────────────────────────────────────────────────────────────

    def _create_tags(self, program):
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(Program)
        for key, value in [
            ('seeded_data',          'true'),
            ('show_preregistration', 'false'),
            ('grade_range_type',     'grade'),
        ]:
            Tag.objects.get_or_create(key=key, content_type=ct, object_id=program.id,
                defaults=dict(value=value))

    # ── QSD ──────────────────────────────────────────────────────────────────

    def _get_nav_cat(self):
        cat, _ = NavBarCategory.objects.get_or_create(name='Dev Navbar',
            defaults=dict(path='/', include_auto_links=True, long_explanation=''))
        return cat

    def _create_global_qsd(self, admin, first_program_name):
        nav_cat = self._get_nav_cat()
        for url, name, title, content in self._global_qsd_pages(first_program_name):
            QuasiStaticData.objects.get_or_create(url=url, name=name, defaults=dict(
                title=title, content=content, author=admin, nav_category=nav_cat,
                create_date=timezone.now(), disabled=False))

    def _create_qsd(self, program, admin):
        nav_cat = self._get_nav_cat()
        for url, name, title, content in self._program_qsd_pages(program.name, program.url):
            QuasiStaticData.objects.get_or_create(url=url, name=name, defaults=dict(
                title=title, content=content, author=admin, nav_category=nav_cat,
                create_date=timezone.now(), disabled=False))

    def _global_qsd_pages(self, program_name):
        """Site-wide pages (only created once; idempotent via get_or_create)."""
        return [
            ('index', 'index', 'Home',
             '## Welcome to the Learning Unlimited Dev Site\n\n'
             'This is a development environment seeded with dummy data.\n\n'
             '### Quick Links\n\n'
             '- [Student Registration](/learn/index.html)\n'
             '- [Teacher Registration](/teach/index.html)\n'
             '- [Volunteer Sign-up](/volunteer/index.html)\n'
             '- [Admin Dashboard](/manage/programs)\n'),

            ('learn/index', 'index', 'Learn with Us',
             '## Upcoming Programs\n\n'
             'Browse our programs and register for classes.\n\n'
             f'- [{program_name}](/learn/{program_name.replace(" ", "")}/2026/studentreg)\n'),

            ('teach/index', 'index', 'Teach with Us',
             '## Teach a Class\n\n'
             'Share your knowledge by teaching at one of our programs.\n\n'
             f'- [{program_name}](/teach/{program_name.replace(" ", "")}/2026/teacherreg)\n'),

            ('volunteer/index', 'index', 'Volunteer',
             '## Volunteer Opportunities\n\n'
             'Help us make our programs a success.\n\n'
             f'- [{program_name}](/volunteer/{program_name.replace(" ", "")}/2026/signup)\n'),

            ('faq', 'faq', 'Frequently Asked Questions',
             '## FAQ\n\n'
             '**Q: Who can take classes?**\n\n'
             'A: Students in grades 7\u201312 are welcome to register.\n\n'
             '**Q: How much does it cost?**\n\n'
             'A: Our programs are free of charge.\n\n'
             '**Q: How do I sign up to teach?**\n\n'
             'A: Create a teacher account and fill out the class registration form.\n\n'
             '**Q: Who are the teachers?**\n\n'
             'A: Our teachers are college students and community volunteers who are passionate about sharing knowledge.\n'),

            ('contact', 'contact', 'Contact Us',
             '## Contact Us\n\n'
             '**Email:** devsite@learningu.org\n\n'
             '**Address:** 84 Massachusetts Ave, Cambridge, MA 02139\n\n'
             'For technical issues, email web-team@learningu.org.\n'),
        ]

    def _program_qsd_pages(self, pn, pu):
        """Per-program QSD pages referenced by templates."""
        return [
            # Student registration flow
            (f'learn/{pu}/studentregheader', 'studentregheader',
             f'{pn} \u2014 Student Registration',
             f'## Welcome to {pn} Registration\n\n'
             'Please complete each step below to finish your registration. '
             'You can save your progress and return at any time.\n'),

            (f'learn/{pu}/studentreg', 'studentreg',
             f'{pn} \u2014 Registration Steps',
             '### Registration Checklist\n\n'
             '1. Fill out your personal information\n'
             '2. Select your classes\n'
             '3. Review and confirm your schedule\n\n'
             '*Tip:* Have a backup class in mind in case your first choice is full.\n'),

            (f'learn/{pu}/studentregfooter', 'studentregfooter',
             f'{pn} \u2014 Registration Footer',
             '---\n\n'
             'Questions about registration? '
             'Email us at devsite@learningu.org.\n'),

            (f'learn/{pu}/catalog', 'catalog',
             f'{pn} \u2014 Course Catalog',
             f'## {pn} Course Catalog\n\n'
             'Browse the classes being offered this session. '
             'Click on a class title to see full details including the teacher bio, '
             'room assignment, and time slot.\n'),

            (f'learn/{pu}/fillslot', 'fillslot',
             f'{pn} \u2014 Choose a Class',
             '## Select a Class for This Time Slot\n\n'
             'The classes below are available during the selected time block. '
             'Click **Add Class** to enroll.\n'),

            (f'learn/{pu}/waitlist', 'waitlist',
             f'{pn} \u2014 Waitlist',
             '## You Have Been Waitlisted\n\n'
             'The class you selected is currently full. '
             'You have been placed on the waitlist and will be notified if a spot opens up.\n'),

            (f'learn/{pu}/medliab', 'medliab',
             f'{pn} \u2014 Medical & Liability',
             '## Medical Information & Liability Waiver\n\n'
             'Please complete the medical liability form before attending the program. '
             'A parent or guardian signature is required for students under 18.\n'),

            (f'learn/{pu}/finaidapp', 'finaidapp',
             f'{pn} \u2014 Financial Aid',
             '## Financial Aid Application\n\n'
             'If you need financial assistance to attend this program, '
             'please fill out the form below. All applications are reviewed confidentially.\n'),

            # Teacher registration flow
            (f'teach/{pu}/teacherreg', 'teacherreg',
             f'Teach at {pn}',
             f'## Teach at {pn}\n\n'
             'Thank you for your interest in teaching! '
             'Please complete the steps below to register your class.\n\n'
             '### What to Expect\n\n'
             '- Fill out your teacher profile\n'
             '- Mark your availability\n'
             '- Submit your class proposal\n'),

            (f'teach/{pu}/classedit_create', 'classedit_create',
             f'{pn} \u2014 Create a Class',
             '## Create a New Class\n\n'
             'Fill in the details for your class below. '
             'Include a clear description so students know what to expect.\n'),

            (f'teach/{pu}/classedit_edit', 'classedit_edit',
             f'{pn} \u2014 Edit Class',
             '## Edit Your Class\n\n'
             'Update the details for your class below. '
             'Changes will be visible to students once saved.\n'),

            (f'teach/{pu}/teacherpreview', 'teacherpreview',
             f'{pn} \u2014 Teacher Dashboard',
             f'## Your {pn} Dashboard\n\n'
             'Here you can view your class details, '
             'check your schedule, and see which students are enrolled.\n'),

            (f'teach/{pu}/teacher_class_import_description', 'teacher_class_import_description',
             f'{pn} \u2014 Import a Class',
             '## Import a Class from a Previous Program\n\n'
             'You can copy a class you previously taught into this program. '
             'Select a class below to pre-fill the form with your old details.\n'),

            # Volunteer flow
            (f'volunteer/{pu}/volunteer_signup', 'volunteer_signup',
             f'Volunteer at {pn}',
             f'## Volunteer at {pn}\n\n'
             'Select the time slots you are available to volunteer. '
             'We will confirm your assignment before the program.\n'),

            (f'volunteer/{pu}/volunteer_complete', 'volunteer_complete',
             f'{pn} \u2014 Volunteer Confirmation',
             '## Thank You for Volunteering!\n\n'
             'Your volunteer sign-up is confirmed. '
             'You will receive an email with further details before the event.\n'),

            (f'volunteer/{pu}/volunteer_cancelled', 'volunteer_cancelled',
             f'{pn} \u2014 Volunteer Cancelled',
             '## Volunteer Sign-up Cancelled\n\n'
             'Your volunteer registration has been cancelled. '
             'If this was a mistake, you can sign up again from the volunteer page.\n'),

            # Onsite / admin
            (f'onsite/{pu}/status', 'status',
             f'{pn} \u2014 Onsite Status',
             f'## {pn} Onsite Status\n\n'
             'Check-in is open. Volunteers, please direct students '
             'to the check-in desk in the main lobby.\n'),

            (f'manage/{pu}/main_bottom', 'main_bottom',
             f'{pn} \u2014 Admin Notes',
             f'## Admin Notes for {pn}\n\n'
             '- Director email: director@example.com\n'
             f'- Program capacity: 200 students\n'
             '- Waitlist enabled: Yes\n'),
        ]

    # ── splash info ───────────────────────────────────────────────────────────

    def _create_splash_info(self, program, students):
        if 'Splash' not in program.name:
            return
        lunch_choices = ['pizza', 'sandwich', 'vegetarian']
        for student in students:
            if not SplashInfo.objects.filter(student=student, program=program).exists():
                info = SplashInfo(
                    student=student, program=program,
                    lunchsat=random.choice(lunch_choices),
                    lunchsun=random.choice(lunch_choices),
                    siblingdiscount=False,
                    siblingname='',
                    submitted=True,
                )
                info.save()

    # ── contact helper ────────────────────────────────────────────────────────

    def _make_contact(self, user, first_name, last_name):
        contact, _ = ContactInfo.objects.get_or_create(
            user=user, first_name=first_name, last_name=last_name,
            defaults=dict(
                e_mail=f'{first_name.lower()}.{last_name.lower()}@example.com',
                phone_day=self.fake.numerify('###-###-####'),
                phone_cell=self.fake.numerify('###-###-####'),
                address_street=self.fake.street_address(),
                address_city=self.fake.city(),
                address_state=self.fake.state_abbr(),
                address_zip=self.fake.numerify('#####'),
                address_country='US',
                receive_txt_message=False,
                undeliverable=False,
            ))
        return contact

    # ── registration profile helper ───────────────────────────────────────────

    def _make_reg_profile(self, user, program, contact_user=None,
                          contact_guardian=None, contact_emergency=None,
                          student_info=None, teacher_info=None, guardian_info=None):
        profile, _ = RegistrationProfile.objects.get_or_create(
            user=user, program=program,
            defaults=dict(
                contact_user=contact_user, contact_guardian=contact_guardian,
                contact_emergency=contact_emergency, student_info=student_info,
                teacher_info=teacher_info, guardian_info=guardian_info,
                most_recent_profile=True, last_ts=timezone.now()))
        return profile