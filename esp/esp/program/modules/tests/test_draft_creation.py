from __future__ import absolute_import
from __future__ import division

import datetime

from django.test import Client

from esp.program.tests import ProgramFrameworkTest
from esp.program.models.class_ import ClassSubject
from esp.program.class_status import ClassStatus
from esp.resources.models import ResourceRequest, ResourceType
from esp.tagdict.models import Tag

# ---------------------------------------------------------------------------
# URL helper
# ---------------------------------------------------------------------------

def _build_url(program, extra):
    """
    Build a teach-tl URL using the same pattern as other module tests:
        program.get_teach_url() -> '/teach/TestProgram/2222_Summer/'
    So full URL is e.g. '/teach/TestProgram/2222_Summer/makeaclass'
    """
    return '{}{}'.format(program.get_teach_url(), extra)


# ---------------------------------------------------------------------------
# Shared settings mixin
# ---------------------------------------------------------------------------

class DraftCreationTestMixin(object):
    """Shared setUp settings for draft tests."""

    DEFAULT_SETTINGS = {
        'num_timeslots': 3,
        'timeslot_length': 50,
        'timeslot_gap': 10,
        'room_capacity': 30,
        'num_categories': 2,
        'num_rooms': 2,
        'num_teachers': 3,
        'classes_per_teacher': 1,
        'sections_per_class': 1,
        'num_students': 2,
        'num_admins': 1,
        'program_type': 'TestProgram',
        'program_instance_name': '2222_Summer',
        'program_instance_label': 'Summer 2222',
        'start_time': datetime.datetime(2222, 7, 7, 7, 5),
    }

    def setUp(self):
        super(DraftCreationTestMixin, self).setUp(**self.DEFAULT_SETTINGS)
        self.client = Client()

        # Set up resource types for testing in a deterministic way
        classroom_type, _ = ResourceType.objects.get_or_create(
            name='Classroom',
            defaults={'description': ''},
        )
        test_resource_type, _ = ResourceType.objects.get_or_create(
            name='Test Resource',
            defaults={'description': ''},
        )
        self.resource_types = [classroom_type, test_resource_type]

    def _make_draft_form_data(self, teacher):
        """Returns valid POST data for draft creation."""
        return {
            'title': 'Draft Class Title',
            'category': self.categories[0].id,
            'class_info': 'A draft description of this class.',
            'prereqs': 'Some prerequisites',
            'duration': self.program.getDurations()[0][0],
            'num_sections': '1',
            'session_count': '1',
            'grade_min': self.program.grade_min,
            'grade_max': self.program.grade_max,
            'class_size_max': '20',
            'class_size_min': '5',
            'class_size_optimal': '15',
            'allow_lateness': 'False',  # RadioSelect value, not checkbox
            'message_for_directors': '',
            'class_reg_page': '1',
            'hardness_rating': '***',
            'class_style': 'Interactive',
            'schedule': 'Schedule info',
            'requested_room': 'Room 101',
            'requested_special_resources': 'Projector and whiteboard',
            'directors_notes': 'Director notes here',
            'purchase_requests': 'Need to buy supplies',
            'request-TOTAL_FORMS': '0',
            'request-INITIAL_FORMS': '0',
            'request-MAX_NUM_FORMS': '1000',
            'restype-TOTAL_FORMS': '0',
            'restype-INITIAL_FORMS': '0',
            'restype-MAX_NUM_FORMS': '1000',
            'save_action': 'draft',  # This is the key for draft saving
        }

    def _make_empty_draft_form_data(self, teacher):
        """Returns POST data with empty required fields to test draft saving with validation bypass."""
        return {
            'title': '',  # Empty title - normally required
            'category': self.categories[0].id,
            'class_info': '',  # Empty description - normally required
            'prereqs': '',
            'duration': self.program.getDurations()[0][0],
            'num_sections': '1',
            'session_count': '1',
            'grade_min': self.program.grade_min,
            'grade_max': self.program.grade_max,
            'class_size_max': '20',
            'class_size_min': '5',
            'class_size_optimal': '15',
            'allow_lateness': 'False',
            'message_for_directors': '',
            'class_reg_page': '1',
            'hardness_rating': '***',
            'class_style': '',  # Empty class style
            'schedule': '',
            'requested_room': '',
            'requested_special_resources': '',
            'directors_notes': '',
            'purchase_requests': '',
            'request-TOTAL_FORMS': '0',
            'request-INITIAL_FORMS': '0',
            'request-MAX_NUM_FORMS': '1000',
            'restype-TOTAL_FORMS': '0',
            'restype-INITIAL_FORMS': '0',
            'restype-MAX_NUM_FORMS': '1000',
            'save_action': 'draft',  # This is the key for draft saving
        }


# ---------------------------------------------------------------------------
# Draft Creation Tests
# ---------------------------------------------------------------------------

class MakeAClassDraftTest(DraftCreationTestMixin, ProgramFrameworkTest):
    """Tests for the makeaclass draft functionality."""

    def _makeaclass_url(self):
        return _build_url(self.program, 'makeaclass')

    def test_save_draft_creates_draft_class(self):
        """A draft POST should create a new ClassSubject with DRAFT status."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )

        before = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT
        ).count()

        response = self.client.post(
            self._makeaclass_url(),
            self._make_draft_form_data(teacher)
        )

        after = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT
        ).count()

        self.assertEqual(after, before + 1,
                         "Expected one new draft class after draft POST")

        # Verify the draft was created with correct data
        draft = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT,
            title='Draft Class Title'
        ).first()

        self.assertIsNotNone(draft, "Draft class should have been created")
        self.assertEqual(draft.title, 'Draft Class Title')
        self.assertEqual(draft.class_info, 'A draft description of this class.')
        self.assertEqual(draft.prereqs, 'Some prerequisites')
        self.assertEqual(draft.hardness_rating, '***')
        self.assertEqual(draft.class_style, 'Interactive')
        self.assertEqual(draft.schedule, 'Schedule info')
        self.assertEqual(draft.requested_room, 'Room 101')
        self.assertEqual(draft.requested_special_resources, 'Projector and whiteboard')
        self.assertEqual(draft.directors_notes, 'Director notes here')
        self.assertEqual(draft.purchase_requests, 'Need to buy supplies')
        self.assertEqual(draft.class_size_min, 5)
        self.assertEqual(draft.class_size_max, 20)  # Fix: match form data
        self.assertEqual(draft.class_size_optimal, 15)
        self.assertEqual(draft.session_count, 1)  # Fix: match form data
        self.assertEqual(draft.allow_lateness, False)

    def test_save_draft_with_empty_required_fields(self):
        """A draft POST should succeed even with empty required fields like title."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )

        before = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT
        ).count()

        response = self.client.post(
            self._makeaclass_url(),
            self._make_empty_draft_form_data(teacher)
        )

        after = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT
        ).count()

        self.assertEqual(after, before + 1,
                         "Expected one new draft class after draft POST with empty fields")

        # Verify the draft was created with empty fields
        draft = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT
        ).first()

        self.assertIsNotNone(draft, "Draft class should have been created even with empty fields")
        self.assertEqual(draft.title, '')  # Empty title - normally required
        self.assertEqual(draft.class_info, '')  # Empty description - normally required
        self.assertEqual(draft.hardness_rating, '***')
        self.assertEqual(draft.class_style, '')  # Empty class style
        self.assertEqual(draft.allow_lateness, False)

    def test_save_draft_redirects_with_success_param(self):
        """A draft POST should redirect with draft_saved=true parameter."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )

        response = self.client.post(
            self._makeaclass_url(),
            self._make_draft_form_data(teacher)
        )

        # Should redirect to same page with draft_saved=true
        self.assertEqual(response.status_code, 302,
                         "Expected redirect after draft save")
        self.assertIn('draft_saved=true', response.url,
                     "Redirect URL should contain draft_saved=true")

    def test_save_draft_updates_existing_draft(self):
        """Saving a draft should update existing draft, not create new one."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )

        # Create first draft
        self.client.post(
            self._makeaclass_url(),
            self._make_draft_form_data(teacher)
        )

        drafts_before = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT
        ).count()

        # Update the draft with different data
        updated_data = self._make_draft_form_data(teacher)
        updated_data['title'] = 'Updated Draft Title'
        updated_data['class_info'] = 'Updated description'
        updated_data['hardness_rating'] = '**'

        response = self.client.post(
            self._makeaclass_url(),
            updated_data
        )

        drafts_after = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT
        ).count()

        # Should still have same number of drafts (updated, not created new)
        self.assertEqual(drafts_after, drafts_before,
                         "Should update existing draft, not create new one")

        # Verify the draft was updated
        draft = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT
        ).first()

        self.assertEqual(draft.title, 'Updated Draft Title')
        self.assertEqual(draft.class_info, 'Updated description')
        self.assertEqual(draft.hardness_rating, '**')

    def test_draft_loads_on_form_display(self):
        """When a draft exists, the form should be populated with draft data."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )

        # Create a draft first
        self.client.post(
            self._makeaclass_url(),
            self._make_draft_form_data(teacher)
        )

        # Now GET the form page - should load with draft data
        response = self.client.get(self._makeaclass_url())

        self.assertEqual(response.status_code, 200,
                         "Expected 200 when accessing makeaclass with existing draft")

        # Check that draft data is in the context
        self.assertIn('class', response.context,
                     "Form context should contain the draft class")
        draft_class = response.context['class']
        self.assertEqual(draft_class.title, 'Draft Class Title')
        self.assertEqual(draft_class.class_info, 'A draft description of this class.')
        self.assertEqual(draft_class.hardness_rating, '***')

    def test_javascript_draft_button_initially_disabled(self):
        """The Save as Draft button should be initially disabled when form loads with draft data."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )

        # Create a draft first
        self.client.post(
            self._makeaclass_url(),
            self._make_draft_form_data(teacher)
        )

        # Now GET the form page - should load with draft data
        response = self.client.get(self._makeaclass_url())

        self.assertEqual(response.status_code, 200,
                         "Expected 200 when accessing makeaclass with existing draft")

        # Check that response contains JavaScript functionality
        self.assertContains(response, 'Save as Draft')
        self.assertContains(response, 'updateDraftButtonState')
        self.assertContains(response, 'hasFormChanged')
        self.assertContains(response, 'initialFormSnapshot')

        # The button should be disabled initially (form hasn't changed yet)
        self.assertContains(response, 'draftButton.disabled = !hasFormChanged()')

    def test_draft_with_resource_requests(self):
        """Draft saving should handle resource requests properly."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )

        # Create draft form data with resource requests
        draft_data = self._make_draft_form_data(teacher)
        draft_data.update({
            'request-TOTAL_FORMS': '2',
            'request-INITIAL_FORMS': '0',
            'request-MAX_NUM_FORMS': '1000',
            'request-0-resource_type': self.resource_types[0].id,
            'request-0-desired_value': 'Projector',
            'request-1-resource_type': self.resource_types[1].id,
            'request-1-desired_value': 'Whiteboard',
        })

        before = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT
        ).count()

        response = self.client.post(
            self._makeaclass_url(),
            draft_data
        )

        after = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT
        ).count()

        self.assertEqual(after, before + 1,
                         "Expected one new draft class with resource requests")

        # Verify resource requests were saved
        draft = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT
        ).first()

        self.assertIsNotNone(draft, "Draft class should have been created")

        # Check resource requests were created for sections
        sections = list(draft.sections.all())
        self.assertTrue(sections,
                        "Draft class should have at least one section to attach resources to")
        section = sections[0]
        resource_requests = ResourceRequest.objects.filter(target=section)
        self.assertGreater(
            resource_requests.count(),
            0,
            "Resource requests should be saved with draft",
        )
        # Verify the specific resource requests from the form data exist
        self.assertTrue(
            resource_requests.filter(
                res_type=self.resource_types[0],
                desired_value='Projector',
            ).exists(),
            "Expected 'Projector' resource request for first resource type",
        )
        self.assertTrue(
            resource_requests.filter(
                res_type=self.resource_types[1],
                desired_value='Whiteboard',
            ).exists(),
            "Expected 'Whiteboard' resource request for second resource type",
        )

    def test_draft_with_all_field_types(self):
        """Draft should save all field types: text, numeric, boolean, FK, M2M."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )

        # Create comprehensive draft data
        draft_data = self._make_draft_form_data(teacher)

        # Add all optional fields to test comprehensive saving
        draft_data.update({
            'class_style': 'Interactive Workshop',
            'schedule': 'Monday 10am-12pm',
            'requested_room': 'Room 101',
            'requested_special_resources': 'Projector, speakers, whiteboard',
            'directors_notes': 'Special notes for directors',
            'purchase_requests': 'Need to buy supplies: markers, paper',
            'class_size_min': '5',
            'class_size_max': '30',
            'class_size_optimal': '15',
            'session_count': '3',
            'allow_lateness': 'True',  # RadioSelect value, matching real form submissions
        })

        # Add size ranges if available
        if hasattr(self, 'size_ranges') and len(self.size_ranges) > 0:
            draft_data['optimal_class_size_range'] = self.size_ranges[0].id
            draft_data['allowable_class_size_ranges'] = [self.size_ranges[0].id, self.size_ranges[1].id]

        response = self.client.post(
            self._makeaclass_url(),
            draft_data
        )

        self.assertEqual(response.status_code, 302,
                         "Expected redirect after draft POST")

        # Verify all fields were saved
        draft = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT
        ).first()

        self.assertIsNotNone(draft, "Draft class should have been created")
        self.assertEqual(draft.class_style, 'Interactive Workshop')
        self.assertEqual(draft.schedule, 'Monday 10am-12pm')
        self.assertEqual(draft.requested_room, 'Room 101')
        self.assertEqual(draft.requested_special_resources, 'Projector, speakers, whiteboard')
        self.assertEqual(draft.directors_notes, 'Special notes for directors')
        self.assertEqual(draft.purchase_requests, 'Need to buy supplies: markers, paper')
        self.assertEqual(draft.class_size_min, 5)
        self.assertEqual(draft.class_size_max, 30)
        self.assertEqual(draft.class_size_optimal, 15)
        self.assertEqual(draft.session_count, 3)
        self.assertEqual(draft.allow_lateness, True)

    def test_draft_edit_workflow(self):
        """Test complete workflow: create draft, edit, save again."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )

        # Step 1: Create initial draft
        initial_data = self._make_draft_form_data(teacher)
        initial_data['title'] = 'Initial Draft Title'
        initial_data['class_info'] = 'Initial description'

        response = self.client.post(
            self._makeaclass_url(),
            initial_data
        )

        # Verify draft created
        draft = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT
        ).first()
        self.assertIsNotNone(draft, "Initial draft should have been created")
        self.assertEqual(draft.title, 'Initial Draft Title')

        # Step 2: Edit the draft
        edit_data = self._make_draft_form_data(teacher)
        edit_data['title'] = 'Updated Draft Title'
        edit_data['class_info'] = 'Updated description'
        edit_data['hardness_rating'] = '****'

        response = self.client.post(
            self._makeaclass_url(),
            edit_data
        )

        # Verify draft was updated (not created new)
        drafts_count = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT
        ).count()
        self.assertEqual(drafts_count, 1,
                         "Should still have only one draft (updated, not created new)")

        # Verify content was updated
        draft.refresh_from_db()
        self.assertEqual(draft.title, 'Updated Draft Title')
        self.assertEqual(draft.class_info, 'Updated description')
        self.assertEqual(draft.hardness_rating, '****')

        # Step 3: Test that we can continue editing the draft
        # (Submit workflow is more complex and requires proper validation)
        final_data = edit_data.copy()
        final_data['title'] = 'Final Draft Title'

        response = self.client.post(
            self._makeaclass_url(),
            final_data
        )

        # Verify draft was updated again
        draft.refresh_from_db()
        self.assertEqual(draft.title, 'Final Draft Title')
        self.assertEqual(draft.status, ClassStatus.DRAFT,
                        "Class should still be draft after final edit")

    def test_draft_permission_isolation(self):
        """Teachers should only see their own drafts, not others' drafts."""
        teacher1 = self.teachers[0]
        teacher2 = self.teachers[1]

        # Create draft for teacher1
        self.assertTrue(
            self.client.login(username=teacher1.username, password='password'),
            "Couldn't log in as teacher %s" % teacher1.username
        )

        teacher1_data = self._make_draft_form_data(teacher1)
        teacher1_data['title'] = 'Teacher1 Draft'

        self.client.post(
            self._makeaclass_url(),
            teacher1_data
        )

        # Create draft for teacher2
        self.assertTrue(
            self.client.login(username=teacher2.username, password='password'),
            "Couldn't log in as teacher %s" % teacher2.username
        )

        teacher2_data = self._make_draft_form_data(teacher2)
        teacher2_data['title'] = 'Teacher2 Draft'

        self.client.post(
            self._makeaclass_url(),
            teacher2_data
        )

        # Teacher1 should only see their own draft
        self.assertTrue(
            self.client.login(username=teacher1.username, password='password'),
            "Couldn't log in as teacher %s" % teacher1.username
        )

        response = self.client.get(self._makeaclass_url())
        self.assertEqual(response.status_code, 200,
                         "Expected 200 when teacher1 accesses makeaclass")

        # Should contain teacher1's draft data, not teacher2's
        self.assertContains(response, 'Teacher1 Draft')
        self.assertNotContains(response, 'Teacher2 Draft',
                          msg_prefix="Teacher1 should not see Teacher2's draft")

    def test_draft_with_custom_fields(self):
        """Draft should persist custom_form_data when custom fields are configured.

        Without the teacherreg_custom_forms Tag the controller sees no custom
        fields, so custom_form_data should remain empty.  This test verifies
        that the draft still saves successfully and that the custom_form_data
        dict is stored (even if empty) rather than being None.
        """
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )

        draft_data = self._make_draft_form_data(teacher)

        response = self.client.post(
            self._makeaclass_url(),
            draft_data
        )

        draft = ClassSubject.objects.filter(
            parent_program=self.program,
            status=ClassStatus.DRAFT
        ).first()

        self.assertIsNotNone(draft, "Draft class should have been created")
        # custom_form_data should be set (possibly empty dict) — never None
        self.assertIsNotNone(draft.custom_form_data,
                             "custom_form_data should be initialised, not None")

    def test_draft_with_multi_select_custom_field(self):
        """Draft should persist all selected values for multi-select custom fields."""
        teacher = self.teachers[0]
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username
        )

        Tag.setTag('teacherreg_custom_forms', value='["ChicagoTeacherQuestionsForm"]')

        draft_data = self._make_draft_form_data(teacher)
        draft_data.update({
            'room_type': 'discussion',
            'std_equipment': ['audio', 'video'],
        })

        response = self.client.post(
            self._makeaclass_url(),
            draft_data
        )

        self.assertIn(response.status_code, [200, 302])

        draft = ClassSubject.objects.filter(
            parent_program=self.program,
            teachers=teacher,
            status=ClassStatus.DRAFT,
        ).first()

        self.assertIsNotNone(draft, "Draft class should have been created")
        self.assertIsNotNone(draft.custom_form_data,
                             "custom_form_data should be initialised, not None")
        self.assertEqual(draft.custom_form_data.get('room_type'), 'discussion')
        self.assertEqual(
            sorted(draft.custom_form_data.get('std_equipment', [])),
            ['audio', 'video'],
            "All selected values from multi-select custom field should be saved",
        )
