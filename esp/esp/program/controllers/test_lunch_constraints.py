import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase

from esp.program.class_status import ClassStatus
from esp.program.controllers.lunch_constraints import LunchConstraintGenerator


class LunchConstraintGeneratorInitializationTest(SimpleTestCase):
    """Tests for initializing LunchConstraintGenerator."""

    @staticmethod
    def make_timeslot(day, hour, timeslot_id):
        return SimpleNamespace(
            start=datetime.datetime.combine(
                day, datetime.time(hour=hour)
            ),
            id=timeslot_id,
            duration=lambda: datetime.timedelta(minutes=60),
        )

    def test_groups_timeslots_before_during_and_after_lunch(self):
        day = datetime.date(2026, 10, 8)
        morning = self.make_timeslot(day, 9, 1)
        lunch = self.make_timeslot(day, 12, 2)
        afternoon = self.make_timeslot(day, 14, 3)

        program = MagicMock()
        program.getTimeSlots.return_value = [
            morning, lunch, afternoon,
        ]

        generator = LunchConstraintGenerator(
            program,
            lunch_timeslots=[lunch],
            generate_constraints=False,
            include_conditions=False,
            autocorrect=False,
        )

        self.assertEqual(generator.days[day]['before'], [morning])
        self.assertEqual(generator.days[day]['lunch'], [lunch])
        self.assertEqual(generator.days[day]['after'], [afternoon])
        self.assertFalse(generator.generate_constraints)
        self.assertFalse(generator.include_conditions)
        self.assertFalse(generator.autocorrect)

    def test_separates_timeslots_by_day(self):
        first_day = datetime.date(2026, 10, 8)
        second_day = datetime.date(2026, 10, 9)

        first_slot = self.make_timeslot(first_day, 9, 1)
        second_slot = self.make_timeslot(second_day, 9, 2)

        program = MagicMock()
        program.getTimeSlots.return_value = [
            first_slot, second_slot,
        ]

        generator = LunchConstraintGenerator(program)

        self.assertEqual(
            generator.days[first_day]['before'],
            [first_slot],
        )
        self.assertEqual(
            generator.days[second_day]['before'],
            [second_slot],
        )
        self.assertEqual(generator.days[first_day]['lunch'], [])
        self.assertEqual(generator.days[second_day]['lunch'], [])

    def test_sorts_lunch_timeslots_by_start_time(self):
        day = datetime.date(2026, 10, 8)
        early_lunch = self.make_timeslot(day, 11, 1)
        late_lunch = self.make_timeslot(day, 12, 2)

        program = MagicMock()
        program.getTimeSlots.return_value = [
            early_lunch, late_lunch,
        ]

        generator = LunchConstraintGenerator(
            program,
            lunch_timeslots=[late_lunch, early_lunch],
        )

        self.assertEqual(
            generator.days[day]['lunch'],
            [early_lunch, late_lunch],
        )


class ApplyBinaryOpToListTest(SimpleTestCase):
    """Tests for apply_binary_op_to_list()."""

    def setUp(self):
        self.generator = LunchConstraintGenerator.__new__(
            LunchConstraintGenerator
        )
        self.expression = MagicMock()

    def test_empty_tokens_do_not_add_anything(self):
        result = self.generator.apply_binary_op_to_list(
            self.expression, 'OR', '0', []
        )

        self.assertIs(result, self.expression)
        self.expression.add_token.assert_not_called()

    def test_single_token_uses_identity_value(self):
        self.generator.apply_binary_op_to_list(
            self.expression, 'OR', '0', ['A']
        )

        self.assertEqual(
            self.expression.add_token.call_args_list,
            [call('A'), call('0'), call('OR')],
        )

    def test_two_tokens_are_combined(self):
        tokens = ['A', 'B']

        self.generator.apply_binary_op_to_list(
            self.expression, 'OR', '0', tokens
        )

        self.assertEqual(
            self.expression.add_token.call_args_list,
            [call('B'), call('A'), call('OR')],
        )
        self.assertEqual(tokens, [])

    def test_multiple_tokens_are_combined_recursively(self):
        self.generator.apply_binary_op_to_list(
            self.expression,
            'OR',
            '0',
            ['A', 'B', 'C', 'D'],
        )

        self.assertEqual(
            self.expression.add_token.call_args_list,
            [
                call('B'),
                call('A'),
                call('OR'),
                call('D'),
                call('C'),
                call('OR'),
                call('OR'),
            ],
        )


class LunchCategoryTest(SimpleTestCase):
    """Tests for retrieving or creating the lunch category."""

    def setUp(self):
        self.generator = LunchConstraintGenerator.__new__(
            LunchConstraintGenerator
        )
        self.generator.program = MagicMock()

    @patch(
        'esp.program.controllers.lunch_constraints.ClassCategories.get_lunch'
    )
    def test_reuses_existing_category(self, get_lunch):
        category = MagicMock()
        get_lunch.return_value = category

        result = self.generator.get_lunch_category()

        self.assertIs(result, category)
        get_lunch.assert_called_once_with()
        self.generator.program.class_categories.add.assert_called_once_with(
            category
        )

    @patch(
        'esp.program.controllers.lunch_constraints.ClassCategories.get_lunch',
        return_value=None,
    )
    @patch(
        'esp.program.controllers.lunch_constraints.ClassCategories.objects.create'
    )
    def test_creates_category_when_missing(
        self, create_category, get_lunch
    ):
        category = MagicMock()
        create_category.return_value = category

        result = self.generator.get_lunch_category()

        self.assertIs(result, category)
        create_category.assert_called_once_with(
            category='Lunch',
            is_lunch=True,
            symbol='L',
        )
        self.generator.program.class_categories.add.assert_called_once_with(
            category
        )


class LunchSubjectTest(SimpleTestCase):
    """Tests for retrieving or creating a lunch subject."""

    def setUp(self):
        self.generator = LunchConstraintGenerator.__new__(
            LunchConstraintGenerator
        )
        self.day = datetime.date(2026, 10, 8)
        self.timeslot = SimpleNamespace(
            duration=lambda: datetime.timedelta(minutes=60),
        )

        self.generator.days = {
            self.day: {
                'before': [],
                'lunch': [self.timeslot],
                'after': [],
            },
        }

        self.generator.program = MagicMock()
        self.generator.program.id = 10
        self.generator.program.program_size_max = 100

    @patch('esp.program.controllers.lunch_constraints.ClassSubject')
    def test_returns_existing_subject(self, subject_model):
        subject = MagicMock()
        subjects = MagicMock()
        subjects.count.return_value = 1
        subjects.__getitem__.return_value = subject
        subject_model.objects.filter.return_value = subjects

        with patch.object(
            self.generator,
            'get_lunch_category',
            return_value=MagicMock(),
        ):
            result = self.generator.get_lunch_subject(self.day)

        self.assertIs(result, subject)
        subject_model.assert_not_called()
        subject.save.assert_not_called()

    @patch('esp.program.controllers.lunch_constraints.ClassSubject')
    def test_creates_subject_when_missing(self, subject_model):
        subjects = MagicMock()
        subjects.count.return_value = 0
        subject_model.objects.filter.return_value = subjects

        new_subject = subject_model.return_value
        category = MagicMock()

        with patch.object(
            self.generator,
            'get_lunch_category',
            return_value=category,
        ):
            result = self.generator.get_lunch_subject(self.day)

        self.assertIs(result, new_subject)
        self.assertEqual(new_subject.grade_min, 7)
        self.assertEqual(new_subject.grade_max, 12)
        self.assertEqual(
            new_subject.parent_program,
            self.generator.program,
        )
        self.assertEqual(new_subject.category, category)
        self.assertEqual(new_subject.class_size_min, 0)
        self.assertEqual(new_subject.class_size_max, 100)
        self.assertEqual(new_subject.duration, '1.0000')
        self.assertEqual(
            new_subject.message_for_directors,
            self.day.isoformat(),
        )
        self.assertEqual(new_subject.title, 'Lunch Period')
        self.assertEqual(new_subject.status, ClassStatus.ACCEPTED)
        self.assertEqual(new_subject.save.call_count, 2)

    @patch('esp.program.controllers.lunch_constraints.ClassSubject')
    def test_uses_fallback_when_program_size_is_unset(
        self, subject_model
    ):
        subjects = MagicMock()
        subjects.count.return_value = 0
        subject_model.objects.filter.return_value = subjects
        self.generator.program.program_size_max = None

        with patch.object(
            self.generator,
            'get_lunch_category',
            return_value=MagicMock(),
        ):
            self.generator.get_lunch_subject(self.day)

        self.assertEqual(
            subject_model.return_value.class_size_max,
            10**6,
        )


class LunchSectionsTest(SimpleTestCase):
    """Tests for retrieving and creating lunch sections."""

    def setUp(self):
        self.generator = LunchConstraintGenerator.__new__(
            LunchConstraintGenerator
        )
        self.day = datetime.date(2026, 10, 8)
        self.timeslot = SimpleNamespace(id=12)

        self.generator.days = {
            self.day: {
                'before': [],
                'lunch': [self.timeslot],
                'after': [],
            },
        }

    def test_creates_section_when_none_exists(self):
        subject = MagicMock()
        subject.sections.filter.return_value.count.return_value = 0

        section = MagicMock()
        subject.add_section.return_value = section
        subject.get_sections.return_value = [section]

        with patch.object(
            self.generator,
            'get_lunch_subject',
            side_effect=[subject, subject],
        ):
            result = self.generator.get_lunch_sections(self.day)

        self.assertEqual(result, [section])
        subject.sections.filter.assert_called_once_with(
            meeting_times__id=12
        )
        subject.add_section.assert_called_once_with(
            status=ClassStatus.ACCEPTED
        )
        section.meeting_times.add.assert_called_once_with(self.timeslot)

    def test_reactivates_existing_sections(self):
        subject = MagicMock()
        existing_section = MagicMock()

        sections = MagicMock()
        sections.count.return_value = 1
        sections.__iter__.return_value = iter([existing_section])
        subject.sections.filter.return_value = sections
        subject.get_sections.return_value = [existing_section]

        with patch.object(
            self.generator,
            'get_lunch_subject',
            side_effect=[subject, subject],
        ):
            result = self.generator.get_lunch_sections(self.day)

        self.assertEqual(result, [existing_section])
        self.assertEqual(
            existing_section.status,
            ClassStatus.ACCEPTED,
        )
        existing_section.save.assert_called_once_with()
        subject.add_section.assert_not_called()


class LunchFailureFunctionTest(SimpleTestCase):
    """Tests for generating the lunch failure callback."""

    def test_includes_lunch_timeslot_ids(self):
        day = datetime.date(2026, 10, 8)
        generator = LunchConstraintGenerator.__new__(
            LunchConstraintGenerator
        )
        generator.days = {
            day: {
                'before': [],
                'lunch': [
                    SimpleNamespace(id=12),
                    SimpleNamespace(id=13),
                ],
                'after': [],
            },
        }

        result = generator.get_failure_function(day)

        self.assertIn('lunch_choices = [12, 13]', result)
        self.assertIn(
            'Unable to autoschedule lunch.',
            result,
        )
        self.assertIn(
            'schedule_map.add_section(dest_sec)',
            result,
        )

    def test_empty_lunch_timeslots_produce_empty_choices(self):
        day = datetime.date(2026, 10, 8)
        generator = LunchConstraintGenerator.__new__(
            LunchConstraintGenerator
        )
        generator.days = {
            day: {
                'before': [],
                'lunch': [],
                'after': [],
            },
        }

        result = generator.get_failure_function(day)

        self.assertIn('lunch_choices = []', result)


class ClearExistingConstraintsTest(SimpleTestCase):
    """Tests for deleting previously generated lunch constraints."""

    @patch('esp.program.controllers.lunch_constraints.ScheduleConstraint')
    @patch('esp.program.controllers.lunch_constraints.ClassSubject')
    @patch('esp.program.controllers.lunch_constraints.ClassSection')
    def test_deletes_old_sections_subjects_and_constraints(
        self,
        section_model,
        subject_model,
        constraint_model,
    ):
        generator = LunchConstraintGenerator.__new__(
            LunchConstraintGenerator
        )
        generator.program = MagicMock()
        generator.lunch_timeslots = [MagicMock()]

        old_section = MagicMock()
        section_model.objects.filter.return_value.exclude.return_value = [
            old_section,
        ]

        old_subject = MagicMock()
        subject_model.objects.filter.return_value = [old_subject]

        old_constraint = MagicMock()
        old_constraint.condition = MagicMock()
        old_constraint.requirement = MagicMock()
        constraint_model.objects.filter.return_value = [old_constraint]

        with patch.object(
            generator,
            'get_lunch_category',
            return_value=MagicMock(),
        ):
            generator.clear_existing_constraints()

        old_section.delete.assert_called_once_with()
        old_subject.delete.assert_called_once_with()
        old_constraint.condition.delete.assert_called_once_with()
        old_constraint.requirement.delete.assert_called_once_with()
        old_constraint.delete.assert_called_once_with()

        section_model.objects.filter.assert_called_once()
        section_model.objects.filter.return_value.exclude.assert_called_once()
        subject_model.objects.filter.assert_called_once()
        constraint_model.objects.filter.assert_called_once_with(
            program=generator.program
        )


class GenerateAllConstraintsTest(SimpleTestCase):
    """Tests for coordinating lunch constraint generation."""

    def setUp(self):
        self.day = datetime.date(2026, 10, 8)
        self.generator = LunchConstraintGenerator.__new__(
            LunchConstraintGenerator
        )
        self.generator.generate_constraints = True
        self.generator.days = {
            self.day: {
                'before': [],
                'lunch': [SimpleNamespace(id=1)],
                'after': [],
            },
        }

    def test_generates_constraint_for_day_with_lunch(self):
        with (
            patch.object(
                self.generator,
                'clear_existing_constraints',
            ) as clear,
            patch.object(
                self.generator,
                'get_lunch_subject',
            ) as get_subject,
            patch.object(
                self.generator,
                'get_lunch_sections',
            ) as get_sections,
            patch.object(
                self.generator,
                'generate_constraint',
            ) as generate,
        ):
            self.generator.generate_all_constraints()

        clear.assert_called_once_with()
        get_subject.assert_called_once_with(self.day)
        get_sections.assert_called_once_with(self.day)
        generate.assert_called_once_with(self.day)

    def test_skips_days_without_lunch_timeslots(self):
        second_day = datetime.date(2026, 10, 9)
        self.generator.days[second_day] = {
            'before': [SimpleNamespace(id=2)],
            'lunch': [],
            'after': [],
        }

        with (
            patch.object(
                self.generator,
                'clear_existing_constraints',
            ),
            patch.object(
                self.generator,
                'get_lunch_subject',
            ) as get_subject,
            patch.object(
                self.generator,
                'get_lunch_sections',
            ) as get_sections,
            patch.object(
                self.generator,
                'generate_constraint',
            ) as generate,
        ):
            self.generator.generate_all_constraints()

        get_subject.assert_called_once_with(self.day)
        get_sections.assert_called_once_with(self.day)
        generate.assert_called_once_with(self.day)

    def test_does_not_generate_constraint_when_disabled(self):
        self.generator.generate_constraints = False

        with (
            patch.object(
                self.generator,
                'clear_existing_constraints',
            ),
            patch.object(
                self.generator,
                'get_lunch_subject',
            ),
            patch.object(
                self.generator,
                'get_lunch_sections',
            ),
            patch.object(
                self.generator,
                'generate_constraint',
            ) as generate,
        ):
            self.generator.generate_all_constraints()

        generate.assert_not_called()


class GenerateConstraintTest(SimpleTestCase):
    """Tests for creating schedule constraints and their expressions."""

    def setUp(self):
        self.day = datetime.date(2026, 10, 8)

        self.morning = SimpleNamespace(id=1)
        self.lunch = SimpleNamespace(id=2)
        self.afternoon = SimpleNamespace(id=3)

        self.generator = LunchConstraintGenerator.__new__(
            LunchConstraintGenerator
        )
        self.generator.program = MagicMock()
        self.generator.program.niceName.return_value = 'Test Program'
        self.generator.days = {
            self.day: {
                'before': [self.morning],
                'lunch': [self.lunch],
                'after': [self.afternoon],
            },
        }
        self.generator.autocorrect = False
        self.generator.include_conditions = True

    @patch(
        'esp.program.controllers.lunch_constraints.ScheduleTestOccupied'
    )
    @patch(
        'esp.program.controllers.lunch_constraints.ScheduleTestCategory'
    )
    @patch(
        'esp.program.controllers.lunch_constraints.ScheduleConstraint'
    )
    @patch(
        'esp.program.controllers.lunch_constraints.BooleanExpression'
    )
    def test_creates_constraint_and_schedule_tests(
        self,
        expression_model,
        constraint_model,
        category_test_model,
        occupied_test_model,
    ):
        requirement = MagicMock()
        requirement.id = 101

        condition = MagicMock()
        condition.id = 102

        expression_model.side_effect = [requirement, condition]

        constraint = constraint_model.return_value

        lunch_test = MagicMock()
        category_test_model.side_effect = [lunch_test]

        morning_test = MagicMock()
        afternoon_test = MagicMock()
        occupied_test_model.side_effect = [
            morning_test,
            afternoon_test,
        ]

        category = MagicMock()

        with patch.object(
            self.generator,
            'get_lunch_category',
            return_value=category,
        ):
            self.generator.generate_constraint(self.day)

        self.assertEqual(
            requirement.label,
            'choose a lunch period on Thursday',
        )
        self.assertEqual(
            condition.label,
            'Test Program lunch constraint check for 2026-10-08',
        )

        requirement.save.assert_called_once_with()
        condition.save.assert_called_once_with()
        constraint.save.assert_called_once_with()

        self.assertEqual(constraint.program, self.generator.program)
        self.assertIs(constraint.condition, condition)
        self.assertIs(constraint.requirement, requirement)

        self.assertEqual(lunch_test.timeblock_id, self.lunch.id)
        self.assertEqual(lunch_test.exp_id, requirement.id)
        self.assertEqual(lunch_test.category, category)

        self.assertEqual(
            category_test_model.call_count,
            1,
        )
        self.assertEqual(
            occupied_test_model.call_count,
            2,
        )

        self.assertEqual(
            morning_test.timeblock_id,
            self.morning.id,
        )
        self.assertEqual(morning_test.exp_id, condition.id)
        self.assertEqual(
            afternoon_test.timeblock_id,
            self.afternoon.id,
        )
        self.assertEqual(afternoon_test.exp_id, condition.id)

        self.assertEqual(
            requirement.add_token.call_args_list,
            [call(lunch_test), call('0'), call('OR')],
        )
        self.assertEqual(
            condition.add_token.call_args_list,
            [
                call(morning_test),
                call('0'),
                call('OR'),
                call(afternoon_test),
                call('0'),
                call('OR'),
                call('AND'),
            ],
        )

    @patch(
        'esp.program.controllers.lunch_constraints.ScheduleTestOccupied'
    )
    @patch(
        'esp.program.controllers.lunch_constraints.ScheduleTestCategory'
    )
    @patch(
        'esp.program.controllers.lunch_constraints.ScheduleConstraint'
    )
    @patch(
        'esp.program.controllers.lunch_constraints.BooleanExpression'
    )
    def test_skips_conditions_when_disabled(
        self,
        expression_model,
        constraint_model,
        category_test_model,
        occupied_test_model,
    ):
        requirement = MagicMock()
        requirement.id = 201

        condition = MagicMock()
        condition.id = 202

        expression_model.side_effect = [requirement, condition]
        self.generator.include_conditions = False

        with patch.object(
            self.generator,
            'get_lunch_category',
            return_value=MagicMock(),
        ):
            self.generator.generate_constraint(self.day)

        self.assertEqual(
            condition.add_token.call_args_list,
            [call('1')],
        )
        occupied_test_model.assert_not_called()
        category_test_model.assert_called_once()