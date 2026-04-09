from datetime import datetime, timedelta

from django.contrib.auth.models import Group

from esp.cal.models import Event, EventType
from esp.program.models import ClassSubject, ProgramModule
from esp.program.modules.base import ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.users.models import ESPUser, Record, RecordType, UserAvailability


class TeacherEventsModuleTest(ProgramFrameworkTest):
    """Tests for TeacherEventsModule: co-teacher slot sharing and
    first-time teacher interview requirement."""

    def setUp(self, *args, **kwargs):
        kwargs.update({'num_teachers': 3, 'classes_per_teacher': 1})
        super().setUp(*args, **kwargs)

        # Create a Teacher Interview event type
        self.interview_type, _ = EventType.objects.get_or_create(
            description='Teacher Interview', defaults={'is_teacher_type': True}
        )
        self.interview_type.is_teacher_type = True
        self.interview_type.save()

        # Create a future interview slot for this program
        future = datetime.now() + timedelta(days=30)
        self.slot = Event.objects.create(
            program=self.program,
            event_type=self.interview_type,
            start=future,
            end=future + timedelta(hours=1),
            short_description='Interview Slot',
            description='Interview Slot',
        )

        # Get the TeacherEventsModule instance
        pm = ProgramModule.objects.get(handler='TeacherEventsModule')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)

        self.teacher_role = Group.objects.get(name='Teacher')

        # teacher1 and teacher2 co-teach a class; teacher3 is unrelated
        self.teacher1 = self.teachers[0]
        self.teacher2 = self.teachers[1]
        self.teacher3 = self.teachers[2]

        # Add teacher2 to teacher1's existing class so they co-teach
        cls = self.teacher1.getTaughtClasses(self.program).first()
        cls.makeTeacher(self.teacher2)

    # --- Subtask 1: co-teacher slot sharing ---

    def _make_request(self, user):
        """Set up a thread-local request for the given user, as the middleware would."""
        from django.test import RequestFactory
        import esp.middleware.threadlocalrequest as tlr
        request = RequestFactory().get('/')
        request.user = user
        tlr._threading_local.request = request
        return request

    def test_unrelated_teacher_cannot_take_occupied_slot(self):
        """A slot booked by teacher1 must not be available to teacher3."""
        UserAvailability.objects.create(
            user=self.teacher1, event=self.slot, role=self.teacher_role
        )
        self._make_request(self.teacher3)
        from esp.program.modules.forms.teacherreg import TeacherEventSignupForm
        form = TeacherEventSignupForm(self.module)
        field_name = 'event_type_%d' % self.interview_type.id
        slot_ids = [int(c[0]) for c in form.fields[field_name].choices if c[0]]
        self.assertNotIn(self.slot.id, slot_ids,
                         "Slot taken by unrelated teacher should not appear for teacher3")

    def test_coteacher_can_take_same_slot(self):
        """A slot booked by teacher1 must still be available to co-teacher teacher2."""
        UserAvailability.objects.create(
            user=self.teacher1, event=self.slot, role=self.teacher_role
        )
        self._make_request(self.teacher2)
        from esp.program.modules.forms.teacherreg import TeacherEventSignupForm
        form = TeacherEventSignupForm(self.module)
        field_name = 'event_type_%d' % self.interview_type.id
        slot_ids = [int(c[0]) for c in form.fields[field_name].choices if c[0]]
        self.assertIn(self.slot.id, slot_ids,
                      "Slot taken by co-teacher should still appear for teacher2")

    # --- Subtask 2: first-time teacher interview requirement ---

    def test_interview_required_for_all_teachers_by_default(self):
        """Without the Tag, interview is required for all teachers."""
        self.module.user = self.teacher1
        self.assertFalse(self.module.isCompleted(self.teacher1),
                         "Interview should be required when no Tag is set")

    def test_interview_required_for_first_time_teacher_with_tag(self):
        """With Tag=first_time, interview is still required for a first-time teacher."""
        Tag.setTag('interview_required_teachers', self.program, 'first_time')
        self.module.user = self.teacher1
        self.assertFalse(self.module.isCompleted(self.teacher1),
                         "Interview should be required for a first-time teacher")

    def test_interview_not_required_for_returning_teacher_with_tag(self):
        """With Tag=first_time, interview is NOT required for a returning teacher."""
        Tag.setTag('interview_required_teachers', self.program, 'first_time')

        # Give teacher1 a prior interview Record from a different program
        rt, _ = RecordType.objects.get_or_create(name='interview')
        past_program = self._make_past_program()
        Record.objects.create(
            user=self.teacher1, event=rt, program=past_program
        )

        self.module.user = self.teacher1
        self.assertTrue(self.module.isCompleted(self.teacher1),
                        "Interview should not be required for a returning teacher")

    def _make_past_program(self):
        """Create a minimal second program to attach a prior Record to."""
        from esp.program.models import Program
        past, _ = Program.objects.get_or_create(
            url='TestProgram/1900_Spring',
            defaults={
                'name': 'TestProgram Spring 1900',
                'grade_min': 7,
                'grade_max': 12,
            }
        )
        return past
