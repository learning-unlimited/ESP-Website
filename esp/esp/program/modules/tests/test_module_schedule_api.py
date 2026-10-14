import json
from datetime import datetime, timedelta

from django.urls import reverse
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import Program, ProgramModule
from esp.program.modules.base import ProgramModuleObj

class TestModuleScheduleAPI(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()

        self.admin = self.admins[0]
        self.student = self.students[0]

        # Grab a real module linked to the program
        mod = ProgramModule.objects.filter(
            id__in=self.program.program_modules.values_list('id', flat=True)
        ).first()

        self.pmo = ProgramModuleObj.getFromProgModule(self.program, mod)

        self.now = datetime.now()
        self.past = self.now - timedelta(days=1)
        self.future = self.now + timedelta(days=1)

        # Kwargs for URL resolution
        self.url_kwargs = {
            'program_type': self.program.program_type,
            'program_term': self.program.program_instance
        }

    def test_module_schedule_api_auth(self):
        """Only admins can access the schedule API."""
        response = self.client.get(reverse("module_schedule_api", kwargs=self.url_kwargs))
        self.assertEqual(response.status_code, 403) # PermissionDenied returns 403

        self.client.force_login(self.student)
        response = self.client.get(reverse("module_schedule_api", kwargs=self.url_kwargs))
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.admin)
        response = self.client.get(reverse("module_schedule_api", kwargs=self.url_kwargs))
        self.assertEqual(response.status_code, 200)

    def test_module_schedule_api_get(self):
        """GET returns grouped modules."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("module_schedule_api", kwargs=self.url_kwargs))
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data["program_id"], self.program.id)
        self.assertIn("learn", data["modules"])

        # Find our pmo in the response
        found = False
        for mod_list in data["modules"].values():
            for m in mod_list:
                if m["id"] == self.pmo.id:
                    found = True
                    break
        self.assertTrue(found)

    def test_module_schedule_update_api(self):
        """PATCH/POST to update saves new dates and seq."""
        self.client.force_login(self.admin)

        payload = {
            "module_id": self.pmo.id,
            "start_date": self.past.isoformat(),
            "end_date": self.future.isoformat(),
            "seq": 999
        }

        response = self.client.post(
            reverse("module_schedule_update_api", kwargs=self.url_kwargs),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])

        # Verify DB updated
        self.pmo.refresh_from_db()
        self.assertEqual(self.pmo.seq, 999)
        self.assertIsNotNone(self.pmo.start_date)
        self.assertIsNotNone(self.pmo.end_date)

    def test_module_schedule_update_validation(self):
        """Cannot set start_date after end_date."""
        self.client.force_login(self.admin)

        payload = {
            "module_id": self.pmo.id,
            "start_date": self.future.isoformat(),
            "end_date": self.past.isoformat()
        }

        response = self.client.post(
            reverse("module_schedule_update_api", kwargs=self.url_kwargs),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data["success"])

    def test_module_schedule_update_syncs_permissions(self):
        """Updating module schedule dates automatically syncs Permission records."""
        self.client.force_login(self.admin)
        from esp.program.models import ProgramModule
        from esp.program.modules.base import ProgramModuleObj
        from esp.users.models import Permission
        from django.contrib.auth.models import Group

        mod = ProgramModule.objects.filter(handler="StudentClassRegModule").first()
        if not mod:
            mod = ProgramModule.objects.create(
                admin_title="Student Class Registration",
                module_type="learn",
                handler="StudentClassRegModule",
                seq=10
            )
        self.program.program_modules.add(mod)
        pmo = ProgramModuleObj.getFromProgModule(self.program, mod)

        student_group = Group.objects.get(name="Student")
        # Ensure no existing permission record for Student/Classes on this program
        Permission.objects.filter(
            program=self.program,
            role=student_group,
            permission_type="Student/Classes"
        ).delete()

        payload = {
            "module_id": pmo.id,
            "start_date": self.past.isoformat(),
            "end_date": self.future.isoformat(),
            "seq": 10
        }

        response = self.client.post(
            reverse("module_schedule_update_api", kwargs=self.url_kwargs),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        # Check DB for created Permission record
        perm = Permission.objects.filter(
            program=self.program,
            role=student_group,
            permission_type="Student/Classes",
            user__isnull=True,
            user_filter__isnull=True
        ).first()
        self.assertIsNotNone(perm)
        self.assertEqual(perm.start_date, self.past)
        self.assertEqual(perm.end_date, self.future)

        # Test updating the dates again
        new_past = self.past - timedelta(days=2)
        new_future = self.future + timedelta(days=2)
        payload = {
            "module_id": pmo.id,
            "start_date": new_past.isoformat(),
            "end_date": new_future.isoformat(),
            "seq": 10
        }
        response = self.client.post(
            reverse("module_schedule_update_api", kwargs=self.url_kwargs),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        perm.refresh_from_db()
        self.assertEqual(perm.start_date, new_past)
        self.assertEqual(perm.end_date, new_future)

        # Also test TeacherClassRegModule
        teacher_mod = ProgramModule.objects.filter(handler="TeacherClassRegModule").first()
        if not teacher_mod:
            teacher_mod = ProgramModule.objects.create(
                admin_title="Teacher Class Registration",
                module_type="teach",
                handler="TeacherClassRegModule",
                seq=10
            )
        self.program.program_modules.add(teacher_mod)
        tpmo = ProgramModuleObj.getFromProgModule(self.program, teacher_mod)
        teacher_group = Group.objects.get(name="Teacher")

        payload = {
            "module_id": tpmo.id,
            "start_date": self.past.isoformat(),
            "end_date": self.future.isoformat(),
            "seq": 10
        }
        response = self.client.post(
            reverse("module_schedule_update_api", kwargs=self.url_kwargs),
            data=json.dumps(payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        tperm = Permission.objects.filter(
            program=self.program,
            role=teacher_group,
            permission_type="Teacher/Classes/All",
            user__isnull=True,
            user_filter__isnull=True
        ).first()
        self.assertIsNotNone(tperm)
        self.assertEqual(tperm.start_date, self.past)
        self.assertEqual(tperm.end_date, self.future)

    def test_module_schedule_preview_api(self):
        """Preview API filters based on `at` timestamp."""
        self.pmo.start_date = self.past
        self.pmo.end_date = self.future
        self.pmo.save()

        self.client.force_login(self.admin)

        # Now (active)
        url = reverse("module_schedule_preview_api", kwargs=self.url_kwargs) + f"?at={self.now.isoformat()}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        found = False
        for mod_list in data["modules"].values():
            for m in mod_list:
                if m["id"] == self.pmo.id:
                    found = True
        self.assertTrue(found)

        # Way past (inactive)
        way_past = self.past - timedelta(days=5)
        url = reverse("module_schedule_preview_api", kwargs=self.url_kwargs) + f"?at={way_past.isoformat()}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        found = False
        for mod_list in data["modules"].values():
            for m in mod_list:
                if m["id"] == self.pmo.id:
                    found = True
        self.assertFalse(found)

    def test_reorder_success(self):
        """POST a valid reorder should update seq values in the DB."""
        self.client.force_login(self.admin)

        # Get another PMO from the program (there should be at least one)
        another_mod = ProgramModule.objects.filter(
            id__in=self.program.program_modules.values_list('id', flat=True)
        ).exclude(id=self.pmo.module.id).first()

        if another_mod is None:
            self.skipTest("Need at least two modules to test reorder.")

        pmo2 = ProgramModuleObj.getFromProgModule(self.program, another_mod)

        url = reverse("module_schedule_reorder_api", kwargs=self.url_kwargs)
        payload = {
            "order": [
                {"id": self.pmo.id, "seq": 50},
                {"id": pmo2.id, "seq": 10}
            ]
        }
        response = self.client.post(url, json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])

        self.pmo.refresh_from_db()
        pmo2.refresh_from_db()
        self.assertEqual(self.pmo.seq, 50)
        self.assertEqual(pmo2.seq, 10)

    def test_reorder_rejects_locked_module(self):
        """Attempting to reorder a position_locked module should return 403 and not save anything."""
        self.client.force_login(self.admin)

        original_seq = self.pmo.seq
        original_handler = self.pmo.module.handler

        # Temporarily make this module locked in the DB
        self.pmo.module.handler = 'StudentRegProfileModule'
        self.pmo.module.save()

        try:
            url = reverse("module_schedule_reorder_api", kwargs=self.url_kwargs)
            payload = {
                "order": [
                    {"id": self.pmo.id, "seq": 999}
                ]
            }
            response = self.client.post(url, json.dumps(payload), content_type="application/json")
            self.assertEqual(response.status_code, 403)
            data = json.loads(response.content)
            self.assertFalse(data["success"])
            self.assertIn("locked", data["error"])
        finally:
            self.pmo.module.handler = original_handler
            self.pmo.module.save()

        # Verify the seq was not changed (transaction was rolled back)
        self.pmo.refresh_from_db()
        self.assertEqual(self.pmo.seq, original_seq)

    def test_reorder_rejects_wrong_program(self):
        """Module IDs from a different program should be silently ignored."""
        from esp.program.models import Program
        self.client.force_login(self.admin)

        # Create a minimal second program and a PMO for it
        prog2 = Program.objects.create(
            url="OtherDev/2026",
            name="Other Dev 2026",
            grade_min=7,
            grade_max=12,
        )
        extra_mod = ProgramModule.objects.filter(
            id__in=self.program.program_modules.values_list('id', flat=True)
        ).first()
        prog2.program_modules.add(extra_mod)
        pmo_other = ProgramModuleObj.getFromProgModule(prog2, extra_mod)
        original_seq = pmo_other.seq

        url = reverse("module_schedule_reorder_api", kwargs=self.url_kwargs)
        payload = {
            "order": [
                {"id": pmo_other.id, "seq": 10}
            ]
        }
        response = self.client.post(url, json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        pmo_other.refresh_from_db()
        # The seq should be unchanged because pmo_other belongs to prog2, not self.program
        self.assertEqual(pmo_other.seq, original_seq)

    def test_reorder_requires_post(self):
        """GET to the reorder endpoint should return 405 Method Not Allowed."""
        self.client.force_login(self.admin)
        url = reverse("module_schedule_reorder_api", kwargs=self.url_kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)



class ModuleScheduleAPITestBase(ProgramFrameworkTest):
    """Shared setup and helpers for the module schedule API edge-case tests."""

    def setUp(self):
        super().setUp()
        self.admin = self.admins[0]
        self.client.force_login(self.admin)

        mod = ProgramModule.objects.filter(
            id__in=self.program.program_modules.values_list('id', flat=True)
        ).first()
        self.pmo = ProgramModuleObj.getFromProgModule(self.program, mod)

        self.url_kwargs = {
            'program_type': self.program.program_type,
            'program_term': self.program.program_instance,
        }

    def post_json(self, url_name, payload):
        return self.client.post(
            reverse(url_name, kwargs=self.url_kwargs),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def get_pmo(self, pmo_id):
        """Re-read a module from the database (bypasses any stale instances)."""
        return ProgramModuleObj.objects.get(pk=pmo_id)


class TestModuleScheduleTimezoneBoundaries(ModuleScheduleAPITestBase):
    """
    Timezone and date edge cases for the update and preview endpoints.

    The site runs with USE_TZ = False and TIME_ZONE = 'America/New_York', so
    aware timestamps sent to the API are converted to naive New York wall-clock
    time before being stored. In 2026, DST starts on Mar 8 (02:00 EST jumps to
    03:00 EDT) and ends on Nov 1 (02:00 EDT falls back to 01:00 EST).
    """

    BASE_START = datetime(2026, 6, 1, 12, 0, 0)
    BASE_END = datetime(2026, 6, 30, 12, 0, 0)

    def update(self, **fields):
        payload = {"module_id": self.pmo.id}
        payload.update(fields)
        return self.post_json("module_schedule_update_api", payload)

    def set_dates(self, start, end):
        self.pmo.start_date = start
        self.pmo.end_date = end
        self.pmo.save()

    def stored_dates(self):
        pmo = self.get_pmo(self.pmo.id)
        return pmo.start_date, pmo.end_date

    def preview_ids(self, at):
        response = self.client.get(
            reverse("module_schedule_preview_api", kwargs=self.url_kwargs),
            {"at": at},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        return {m["id"] for mods in data["modules"].values() for m in mods}

    # ---- DST transitions -------------------------------------------------

    def test_spring_forward_aware_inputs_convert_to_wall_clock(self):
        """Instants either side of the spring-forward gap map to 01:59:59 EST and 03:00:00 EDT."""
        response = self.update(
            start_date="2026-03-08T06:59:59+00:00",  # 01:59:59 EST
            end_date="2026-03-08T07:00:00+00:00",    # 03:00:00 EDT
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["start_date"], "2026-03-08T01:59:59")
        self.assertEqual(data["end_date"], "2026-03-08T03:00:00")
        self.assertEqual(
            self.stored_dates(),
            (datetime(2026, 3, 8, 1, 59, 59), datetime(2026, 3, 8, 3, 0, 0)),
        )

    def test_spring_forward_non_utc_offset_matches_utc(self):
        """An explicit -05:00 offset (EST) is converted the same way as the equivalent UTC instant."""
        response = self.update(
            start_date="2026-03-08T01:59:59-05:00",
            end_date="2026-03-08T03:00:00-04:00",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.stored_dates(),
            (datetime(2026, 3, 8, 1, 59, 59), datetime(2026, 3, 8, 3, 0, 0)),
        )

    def test_spring_forward_nonexistent_local_time_is_shifted_by_database(self):
        """
        A naive 02:30 on the spring-forward date does not exist locally. The API
        accepts it without error, but PostgreSQL interprets it in the session
        time zone (America/New_York) and moves it forward an hour to 03:30.
        """
        response = self.update(
            start_date="2026-03-08T02:30:00",
            end_date="2026-03-08T04:00:00",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.stored_dates(),
            (datetime(2026, 3, 8, 3, 30, 0), datetime(2026, 3, 8, 4, 0, 0)),
        )

    def test_fall_back_ambiguous_local_time_is_stored_as_given(self):
        """A naive 01:30 on the fall-back date occurs twice locally; it is stored unchanged without error."""
        response = self.update(
            start_date="2026-11-01T01:30:00",
            end_date="2026-11-01T03:00:00",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.stored_dates(),
            (datetime(2026, 11, 1, 1, 30, 0), datetime(2026, 11, 1, 3, 0, 0)),
        )

    def test_fall_back_both_ambiguous_instants_map_to_same_wall_clock(self):
        """
        01:30 EDT (05:30Z) and 01:30 EST (06:30Z) are an hour apart in real
        time, but both become naive 01:30. Each converts correctly on its own,
        but as a start/end pair they collapse to start == end and are rejected.
        """
        self.set_dates(None, None)
        for utc_instant in ("2026-11-01T05:30:00Z", "2026-11-01T06:30:00Z"):
            with self.subTest(utc_instant=utc_instant):
                response = self.update(start_date=utc_instant)
                self.assertEqual(response.status_code, 200)
                start, _ = self.stored_dates()
                self.assertEqual(start, datetime(2026, 11, 1, 1, 30, 0))

        self.set_dates(self.BASE_START, self.BASE_END)
        response = self.update(
            start_date="2026-11-01T05:30:00Z",
            end_date="2026-11-01T06:30:00Z",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(json.loads(response.content)["success"])
        self.assertEqual(self.stored_dates(), (self.BASE_START, self.BASE_END))

    def test_fall_back_range_spanning_transition(self):
        """A range spanning the repeated hour converts both ends to local wall-clock time."""
        response = self.update(
            start_date="2026-11-01T04:30:00Z",  # 00:30 EDT
            end_date="2026-11-01T07:30:00Z",    # 02:30 EST
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.stored_dates(),
            (datetime(2026, 11, 1, 0, 30, 0), datetime(2026, 11, 1, 2, 30, 0)),
        )

    # ---- Partial updates -------------------------------------------------

    def test_partial_update_start_only_validated_against_existing_end(self):
        """Sending only start_date compares it with the end_date already in the database."""
        cases = [
            ("after existing end", "2026-07-01T00:00:00", 400),
            ("equal to existing end", "2026-06-30T12:00:00", 400),
            ("before existing end", "2026-05-01T00:00:00", 200),
        ]
        for label, value, expected_status in cases:
            with self.subTest(label):
                self.set_dates(self.BASE_START, self.BASE_END)
                response = self.update(start_date=value)
                self.assertEqual(response.status_code, expected_status)
                start, end = self.stored_dates()
                self.assertEqual(end, self.BASE_END)
                if expected_status == 200:
                    self.assertEqual(start, datetime.fromisoformat(value))
                else:
                    self.assertEqual(start, self.BASE_START)

    def test_partial_update_end_only_validated_against_existing_start(self):
        """Sending only end_date compares it with the start_date already in the database."""
        cases = [
            ("before existing start", "2026-05-01T00:00:00", 400),
            ("equal to existing start", "2026-06-01T12:00:00", 400),
            ("after existing start", "2026-08-01T00:00:00", 200),
        ]
        for label, value, expected_status in cases:
            with self.subTest(label):
                self.set_dates(self.BASE_START, self.BASE_END)
                response = self.update(end_date=value)
                self.assertEqual(response.status_code, expected_status)
                start, end = self.stored_dates()
                self.assertEqual(start, self.BASE_START)
                if expected_status == 200:
                    self.assertEqual(end, datetime.fromisoformat(value))
                else:
                    self.assertEqual(end, self.BASE_END)

    def test_invalid_date_strings_rejected_without_changes(self):
        """Malformed and impossible date strings return 400 and leave stored dates alone."""
        for field in ("start_date", "end_date"):
            for bad in ("not-a-date", "2026-13-45T00:00:00"):
                with self.subTest(field=field, value=bad):
                    self.set_dates(self.BASE_START, self.BASE_END)
                    response = self.update(**{field: bad})
                    self.assertEqual(response.status_code, 400)
                    self.assertFalse(json.loads(response.content)["success"])
                    self.assertEqual(self.stored_dates(), (self.BASE_START, self.BASE_END))

    # ---- Clearing dates --------------------------------------------------

    def test_clear_dates_with_none_and_empty_string(self):
        """None and '' both clear a date; the other date is untouched."""
        for empty in (None, ""):
            with self.subTest(empty=empty):
                self.set_dates(self.BASE_START, self.BASE_END)

                response = self.update(start_date=empty)
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(json.loads(response.content)["start_date"])
                self.assertEqual(self.stored_dates(), (None, self.BASE_END))

                self.set_dates(self.BASE_START, self.BASE_END)
                response = self.update(end_date=empty)
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(json.loads(response.content)["end_date"])
                self.assertEqual(self.stored_dates(), (self.BASE_START, None))

                self.set_dates(self.BASE_START, self.BASE_END)
                response = self.update(start_date=empty, end_date=empty)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.stored_dates(), (None, None))

    def test_cleared_dates_make_module_always_valid_in_preview(self):
        """A module with no dates shows up in the preview at any timestamp."""
        self.set_dates(self.BASE_START, self.BASE_END)
        self.assertNotIn(self.pmo.id, self.preview_ids("2020-01-01T00:00:00"))

        self.update(start_date=None, end_date="")
        for at in ("1999-01-01T00:00:00", "2026-06-15T00:00:00", "2099-12-31T23:59:59"):
            with self.subTest(at=at):
                self.assertIn(self.pmo.id, self.preview_ids(at))

    # ---- Microsecond precision -------------------------------------------

    def test_microsecond_precision_round_trip_naive(self):
        """Microseconds in naive input survive storage, the update response, and the GET API."""
        response = self.update(
            start_date="2026-06-01T12:00:00.123456",
            end_date="2026-06-01T12:00:00.654321",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["start_date"], "2026-06-01T12:00:00.123456")
        self.assertEqual(data["end_date"], "2026-06-01T12:00:00.654321")

        start, end = self.stored_dates()
        self.assertEqual(start.microsecond, 123456)
        self.assertEqual(end.microsecond, 654321)

        listing = json.loads(
            self.client.get(reverse("module_schedule_api", kwargs=self.url_kwargs)).content
        )
        entry = next(
            m for mods in listing["modules"].values() for m in mods if m["id"] == self.pmo.id
        )
        self.assertEqual(entry["start_date"], "2026-06-01T12:00:00.123456")
        self.assertEqual(entry["end_date"], "2026-06-01T12:00:00.654321")

    def test_microsecond_precision_preserved_through_timezone_conversion(self):
        """Converting an aware timestamp to local time does not drop microseconds."""
        response = self.update(
            start_date="2026-06-01T16:00:00.654321+00:00",  # 12:00:00.654321 EDT
            end_date="2026-06-01T16:00:01.000001+00:00",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.stored_dates(),
            (datetime(2026, 6, 1, 12, 0, 0, 654321), datetime(2026, 6, 1, 12, 0, 1, 1)),
        )

    def test_preview_boundaries_are_microsecond_exact_and_inclusive(self):
        """Preview treats start and end as inclusive and distinguishes a single microsecond."""
        self.set_dates(
            datetime(2026, 6, 1, 12, 0, 0, 500000),
            datetime(2026, 6, 1, 13, 0, 0, 500000),
        )
        cases = [
            ("2026-06-01T12:00:00.499999", False),
            ("2026-06-01T12:00:00.500000", True),
            ("2026-06-01T13:00:00.500000", True),
            ("2026-06-01T13:00:00.500001", False),
        ]
        for at, expected in cases:
            with self.subTest(at=at):
                self.assertEqual(self.pmo.id in self.preview_ids(at), expected)

    # ---- Calendar year boundary ------------------------------------------

    def test_preview_across_new_year_boundary(self):
        """A module that is active across Dec 31 / Jan 1 is previewed correctly on both sides."""
        self.set_dates(
            datetime(2026, 12, 31, 23, 59, 59),
            datetime(2027, 1, 1, 0, 0, 1),
        )
        cases = [
            ("2026-12-31T23:59:58", False),
            ("2026-12-31T23:59:59", True),
            ("2027-01-01T00:00:00", True),
            ("2027-01-01T00:00:01", True),
            ("2027-01-01T00:00:02", False),
        ]
        for at, expected in cases:
            with self.subTest(at=at):
                self.assertEqual(self.pmo.id in self.preview_ids(at), expected)

    def test_preview_new_year_boundary_with_aware_timestamp(self):
        """An aware 'at' just after midnight UTC on Jan 1 is still Dec 31 in New York."""
        self.set_dates(
            datetime(2026, 12, 31, 23, 59, 59),
            datetime(2026, 12, 31, 23, 59, 59),
        )
        # 04:59:59Z on Jan 1 == 23:59:59 EST on Dec 31
        self.assertIn(self.pmo.id, self.preview_ids("2027-01-01T04:59:59Z"))
        # one second earlier is 23:59:58 EST, before the module starts
        self.assertNotIn(self.pmo.id, self.preview_ids("2027-01-01T04:59:58Z"))
        # 05:00:00Z is midnight EST on Jan 1, after the module ends
        self.assertNotIn(self.pmo.id, self.preview_ids("2027-01-01T05:00:00Z"))


class TestModuleScheduleReorderBulk(ModuleScheduleAPITestBase):
    """Bulk-update edge cases for module_schedule_reorder_api."""

    POSITION_LOCKED_HANDLERS = (
        'StudentRegProfileModule',
        'TeacherRegProfileModule',
        'CreditCardModule_stripe',
        'StudentRegConfirm',
    )

    @staticmethod
    def is_position_locked(handler):
        return (
            handler in ('StudentRegProfileModule', 'TeacherRegProfileModule')
            or 'CreditCardModule_' in handler
            or handler == 'StudentRegConfirm'
        )

    def setUp(self):
        super().setUp()
        self.reorder_url = reverse("module_schedule_reorder_api", kwargs=self.url_kwargs)

        self.unlocked = []
        modules = ProgramModule.objects.filter(
            id__in=self.program.program_modules.values_list('id', flat=True)
        ).order_by('id')
        for module in modules:
            if not self.is_position_locked(module.handler):
                self.unlocked.append(ProgramModuleObj.getFromProgModule(self.program, module))
        if len(self.unlocked) < 4:
            self.skipTest("Need at least four unlocked modules to test bulk reordering.")

    def reorder(self, order):
        return self.post_json("module_schedule_reorder_api", {"order": order})

    def seq_of(self, pmo):
        return self.get_pmo(pmo.id).seq

    def snapshot(self, pmos):
        return {pmo.id: self.seq_of(pmo) for pmo in pmos}

    def lock(self, pmo, handler='StudentRegProfileModule'):
        """Make a module position-locked by pointing its ProgramModule at a locked handler."""
        ProgramModule.objects.filter(pk=pmo.module.id).update(handler=handler)

    # ---- Large and mixed batches -----------------------------------------

    def test_large_batch_reorders_every_module(self):
        """Reversing the order of every unlocked module in the program updates all of them."""
        count = len(self.unlocked)
        expected = {
            pmo.id: 1000 + (count - i) * 10 for i, pmo in enumerate(self.unlocked)
        }
        response = self.reorder([{"id": pk, "seq": seq} for pk, seq in expected.items()])
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)["success"])
        self.assertEqual(self.snapshot(self.unlocked), expected)

    def test_duplicate_ids_in_one_batch_last_entry_wins(self):
        """When the same module appears twice, the later entry determines the final seq."""
        target = self.unlocked[0]
        response = self.reorder([
            {"id": target.id, "seq": 5},
            {"id": target.id, "seq": 7},
        ])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.seq_of(target), 7)

    def test_mixed_payload_applies_only_modules_of_this_program(self):
        """Valid local ids are applied; foreign-program and non-existent ids are ignored."""
        local_a, local_b = self.unlocked[0], self.unlocked[1]

        other_program = Program.objects.create(
            url="OtherDev/2027",
            name="Other Dev 2027",
            grade_min=7,
            grade_max=12,
        )
        other_program.program_modules.add(local_a.module)
        foreign = ProgramModuleObj.getFromProgModule(other_program, local_a.module)
        foreign_seq = foreign.seq
        missing_id = ProgramModuleObj.objects.order_by('-id').first().id + 10000

        response = self.reorder([
            {"id": local_a.id, "seq": 4001},
            {"id": foreign.id, "seq": 4002},
            {"id": missing_id, "seq": 4003},
            {"id": local_b.id, "seq": 4004},
        ])
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)["success"])

        self.assertEqual(self.seq_of(local_a), 4001)
        self.assertEqual(self.seq_of(local_b), 4004)
        self.assertEqual(self.seq_of(foreign), foreign_seq)
        self.assertFalse(ProgramModuleObj.objects.filter(pk=missing_id).exists())

    # ---- Position-locked modules -----------------------------------------

    def test_each_position_locked_handler_is_rejected_even_if_seq_unchanged(self):
        """Any entry for a locked module is rejected, even when it re-submits the current seq."""
        target = self.unlocked[0]
        original_seq = self.seq_of(target)
        for handler in self.POSITION_LOCKED_HANDLERS:
            with self.subTest(handler=handler):
                self.lock(target, handler)
                response = self.reorder([{"id": target.id, "seq": original_seq}])
                self.assertEqual(response.status_code, 403)
                data = json.loads(response.content)
                self.assertFalse(data["success"])
                self.assertIn("locked", data["error"])
                self.assertEqual(self.seq_of(target), original_seq)

    def test_locked_module_anywhere_in_batch_rolls_back_everything(self):
        """A locked module at the front, middle, or end of a batch aborts the whole transaction."""
        first, second, third, locked = self.unlocked[:4]
        self.lock(locked)
        movable = [first, second, third]

        for position in ("front", "middle", "end"):
            with self.subTest(position=position):
                before = self.snapshot(movable)
                entries = [
                    {"id": pmo.id, "seq": 5000 + i} for i, pmo in enumerate(movable)
                ]
                locked_entry = {"id": locked.id, "seq": 9999}
                index = {"front": 0, "middle": 2, "end": len(entries)}[position]
                entries.insert(index, locked_entry)

                response = self.reorder(entries)
                self.assertEqual(response.status_code, 403)
                self.assertFalse(json.loads(response.content)["success"])
                self.assertEqual(self.snapshot(movable), before)

    # ---- Malformed and boundary payloads ---------------------------------

    def test_empty_payloads_are_successful_no_ops(self):
        """An empty body object, empty order list, and id-less entries change nothing."""
        before = self.snapshot(self.unlocked)
        payloads = [
            {},
            {"order": []},
            {"order": [{}]},
            {"order": [{"seq": 5}]},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.post_json("module_schedule_reorder_api", payload)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(json.loads(response.content)["success"])
                self.assertEqual(self.snapshot(self.unlocked), before)

    def test_order_must_be_a_list(self):
        """A non-list 'order' value is rejected with 400."""
        for bad in ("abc", {}, {"id": 1, "seq": 2}, 5, None):
            with self.subTest(order=bad):
                response = self.post_json("module_schedule_reorder_api", {"order": bad})
                self.assertEqual(response.status_code, 400)
                self.assertFalse(json.loads(response.content)["success"])

    def test_non_dict_entries_are_rejected(self):
        """Entries that are not objects return 400 and change nothing."""
        before = self.snapshot(self.unlocked)
        for bad_entry in (1, None):
            with self.subTest(entry=bad_entry):
                response = self.reorder([bad_entry])
                self.assertEqual(response.status_code, 400)
                self.assertFalse(json.loads(response.content)["success"])
                self.assertEqual(self.snapshot(self.unlocked), before)

    def test_invalid_json_body_is_rejected(self):
        """A body that is not valid JSON returns 400."""
        response = self.client.post(
            self.reorder_url, data="{not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(json.loads(response.content)["success"])

    def test_non_integer_sequences_are_rejected_without_changes(self):
        """Non-integer or missing seq values return 400, and earlier entries in the batch are rolled back."""
        good, target = self.unlocked[0], self.unlocked[1]
        before = self.snapshot([good, target])
        for bad_seq in ("abc", "1.5", "", None, [], {}):
            with self.subTest(seq=bad_seq):
                response = self.reorder([
                    {"id": good.id, "seq": 6001},
                    {"id": target.id, "seq": bad_seq},
                ])
                self.assertEqual(response.status_code, 400)
                self.assertFalse(json.loads(response.content)["success"])
                self.assertEqual(self.snapshot([good, target]), before)

        with self.subTest("missing seq key"):
            response = self.reorder([{"id": target.id}])
            self.assertEqual(response.status_code, 400)
            self.assertEqual(self.snapshot([good, target]), before)

    def test_numeric_string_sequence_is_accepted(self):
        """A seq given as a numeric string is coerced to an integer."""
        target = self.unlocked[0]
        response = self.reorder([{"id": target.id, "seq": "42"}])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.seq_of(target), 42)

    def test_32_bit_integer_limits(self):
        """The extremes of a 32-bit signed integer are accepted."""
        high, low = self.unlocked[0], self.unlocked[1]
        response = self.reorder([
            {"id": high.id, "seq": 2147483647},
            {"id": low.id, "seq": -2147483648},
        ])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.seq_of(high), 2147483647)
        self.assertEqual(self.seq_of(low), -2147483648)

    def test_out_of_range_sequences_fail_and_roll_back(self):
        """
        Values just outside the 32-bit range cannot be stored. The request must
        fail (the exact error status is not pinned) and earlier entries in the
        same batch must be rolled back.
        """
        good, target = self.unlocked[0], self.unlocked[1]
        before = self.snapshot([good, target])
        for bad_seq in (2147483648, -2147483649):
            with self.subTest(seq=bad_seq):
                response = self.reorder([
                    {"id": good.id, "seq": 7001},
                    {"id": target.id, "seq": bad_seq},
                ])
                self.assertGreaterEqual(response.status_code, 400)
                self.assertFalse(json.loads(response.content)["success"])
                self.assertEqual(self.snapshot([good, target]), before)

    # ---- Idempotency -----------------------------------------------------

    def test_reorder_is_idempotent(self):
        """Submitting the same reorder twice succeeds both times and yields the same state."""
        entries = [
            {"id": pmo.id, "seq": 8000 + i * 10} for i, pmo in enumerate(self.unlocked)
        ]
        first = self.reorder(entries)
        self.assertEqual(first.status_code, 200)
        after_first = self.snapshot(self.unlocked)

        second = self.reorder(entries)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(self.snapshot(self.unlocked), after_first)
        self.assertEqual(
            after_first, {e["id"]: e["seq"] for e in entries}
        )
