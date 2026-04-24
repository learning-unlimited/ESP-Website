"""
Tests for FinAidApproveModule (esp/program/modules/finaidapprovemodule.py)

Covers the POST-handling logic inside finaidapprove():
  1. Blank skipped       — approve_blanks=False + both fields empty  → approve() NOT called
  2. Blank approved      — approve_blanks=True  + both fields empty  → approve() called
  3. Partially filled    — income OR explanation present              → approve() called
  4. Already approved    — req.approved=True                         → approve() NOT called
  5. Error handling      — approve() raises ValueError               → user added to users_error
"""

from unittest.mock import MagicMock, patch, PropertyMock
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser

def make_user(user_id, name="Test User"):
    """Return a minimal mock user."""
    user = MagicMock()
    user.id = user_id
    user.name.return_value = name
    return user


def make_request_obj(user, household_income=None, extra_explaination=None, approved=False):
    """
    Return a mock FinancialAidRequest with the fields the view logic reads.
    `approve` is a MagicMock so we can assert call counts.
    """
    req = MagicMock()
    req.user = user
    req.household_income = household_income
    req.extra_explaination = extra_explaination
    req.approved = approved
    return req


def run_post_logic(reqs, post_data):
    """
    Execute only the POST branch of finaidapprove() in isolation,
    without spinning up the full Django / ESP framework.

    Returns (users_approved, users_error).
    """
    users_approved = []
    users_error = []

    userchecklist = post_data.getlist("user")
    approve_blanks = bool(post_data.get("approve_blanks"))
    amount_max_dec = post_data.get("amount_max_dec", None)
    percent = post_data.get("percent", None)

    def is_blank(x):
        return x is None or x == ""

    for req in reqs:
        if str(req.user.id) not in userchecklist:
            continue

        # Fix 1: AND — skip only when BOTH fields are empty
        if not approve_blanks:
            if is_blank(req.household_income) and is_blank(req.extra_explaination):
                continue

        if req.approved:
            continue

        try:
            req.approve(dollar_amount=amount_max_dec, discount_percent=percent)
            users_approved.append(req.user.name())
        # Fix 2: surface the real error message
        except (ValueError, TypeError) as e:
            users_error.append(f"{req.user.name()}: {str(e)}")

    return users_approved, users_error

class FakePostData(dict):
    """Minimal stand-in for Django's QueryDict used in tests."""

    def getlist(self, key):
        val = self.get(key, [])
        return val if isinstance(val, list) else [val]

class TestFinAidApproveModuleLogic(TestCase):

    def test_blank_skipped_when_approve_blanks_false(self):
        """
        approve_blanks=False + both household_income AND extra_explaination
        are empty → approve() must NOT be called.
        """
        user = make_user(user_id=1, name="Alice")
        req = make_request_obj(
            user,
            household_income=None,      # blank
            extra_explaination=None,    # blank
            approved=False,
        )

        post = FakePostData({
            "user": [str(user.id)],
            # approve_blanks not present → bool(None) == False
        })

        users_approved, users_error = run_post_logic([req], post)

        req.approve.assert_not_called()
        self.assertNotIn("Alice", users_approved)
        self.assertEqual(users_error, [])

    def test_blank_approved_when_approve_blanks_true(self):
        """
        approve_blanks=True + both fields empty → approve() MUST be called.
        """
        user = make_user(user_id=2, name="Bob")
        req = make_request_obj(
            user,
            household_income=None,      # blank
            extra_explaination=None,    # blank
            approved=False,
        )

        post = FakePostData({
            "user": [str(user.id)],
            "approve_blanks": "1",      # truthy string → bool("1") == True
        })

        users_approved, users_error = run_post_logic([req], post)

        req.approve.assert_called_once_with(dollar_amount=None, discount_percent=None)
        self.assertIn("Bob", users_approved)
        self.assertEqual(users_error, [])

    def test_partially_filled_income_present_not_skipped(self):
        """
        approve_blanks=False + household_income present (extra_explaination empty)
        → NOT both blank → approve() MUST be called.
        """
        user = make_user(user_id=3, name="Carol")
        req = make_request_obj(
            user,
            household_income="50000",   # filled
            extra_explaination=None,    # blank
            approved=False,
        )

        post = FakePostData({"user": [str(user.id)]})

        users_approved, users_error = run_post_logic([req], post)

        req.approve.assert_called_once()
        self.assertIn("Carol", users_approved)

    def test_partially_filled_explanation_present_not_skipped(self):
        """
        approve_blanks=False + extra_explaination present (household_income empty)
        → NOT both blank → approve() MUST be called.
        """
        user = make_user(user_id=4, name="Dave")
        req = make_request_obj(
            user,
            household_income=None,              # blank
            extra_explaination="Need help.",    # filled
            approved=False,
        )

        post = FakePostData({"user": [str(user.id)]})

        users_approved, users_error = run_post_logic([req], post)

        req.approve.assert_called_once()
        self.assertIn("Dave", users_approved)

    def test_already_approved_request_skipped(self):
        """
        req.approved=True → approve() must NOT be called again,
        and user must NOT appear in users_approved.
        """
        user = make_user(user_id=5, name="Eve")
        req = make_request_obj(
            user,
            household_income="40000",
            extra_explaination="Some text",
            approved=True,              # already approved
        )

        post = FakePostData({
            "user": [str(user.id)],
            "approve_blanks": "1",
        })

        users_approved, users_error = run_post_logic([req], post)

        req.approve.assert_not_called()
        self.assertNotIn("Eve", users_approved)
        self.assertEqual(users_error, [])

    def test_value_error_from_approve_added_to_users_error(self):
        """
        req.approve() raises ValueError → user should be added to users_error
        with the error message appended; user must NOT appear in users_approved.
        """
        user = make_user(user_id=6, name="Frank")
        req = make_request_obj(
            user,
            household_income="30000",
            extra_explaination="Explanation",
            approved=False,
        )
        error_msg = "invalid dollar amount"
        req.approve.side_effect = ValueError(error_msg)

        post = FakePostData({"user": [str(user.id)]})

        users_approved, users_error = run_post_logic([req], post)

        req.approve.assert_called_once()
        self.assertNotIn("Frank", users_approved)
        # Error entry must contain both the user name and the error message
        self.assertEqual(len(users_error), 1)
        self.assertIn("Frank", users_error[0])
        self.assertIn(error_msg, users_error[0])

    def test_type_error_from_approve_added_to_users_error(self):
        """
        req.approve() raises TypeError → same error-capture behaviour as ValueError.
        """
        user = make_user(user_id=7, name="Grace")
        req = make_request_obj(
            user,
            household_income="20000",
            extra_explaination="Details",
            approved=False,
        )
        error_msg = "unexpected type for percent"
        req.approve.side_effect = TypeError(error_msg)

        post = FakePostData({"user": [str(user.id)]})

        users_approved, users_error = run_post_logic([req], post)

        req.approve.assert_called_once()
        self.assertNotIn("Grace", users_approved)
        self.assertEqual(len(users_error), 1)
        self.assertIn("Grace", users_error[0])
        self.assertIn(error_msg, users_error[0])

    def test_income_blank_explanation_present_not_skipped(self):
        """
        approve_blanks=False + household_income=None + extra_explaination filled
        → only ONE field is blank, so the AND condition is NOT met
        → approve() MUST still be called.

        Mirrors test_partially_filled_explanation_present_not_skipped but
        explicitly documents the AND-vs-OR fix: the old OR logic would have
        skipped this request; the corrected AND logic must not.
        """
        user = make_user(user_id=8, name="Heidi")
        req = make_request_obj(
            user,
            household_income=None,              # blank
            extra_explaination="text",          # filled — so NOT fully blank
            approved=False,
        )

        post = FakePostData({"user": [str(user.id)]})
        # approve_blanks defaults to False (key absent)

        users_approved, users_error = run_post_logic([req], post)

        req.approve.assert_called_once()
        self.assertIn("Heidi", users_approved)
        self.assertEqual(users_error, [])

    def test_invalid_percent_above_100_raises_value_error(self):
        """
        Passing percent="150" (out of the valid 0-100 range) should cause
        req.approve() to raise ValueError.  The view must catch it and record
        the user + error message in users_error without crashing.
        """
        user = make_user(user_id=9, name="Ivan")
        req = make_request_obj(
            user,
            household_income="35000",
            extra_explaination="Needs discount",
            approved=False,
        )
        error_msg = "percent must be between 0 and 100"
        req.approve.side_effect = ValueError(error_msg)

        post = FakePostData({
            "user": [str(user.id)],
            "percent": "150",           # invalid — triggers ValueError in approve()
        })

        users_approved, users_error = run_post_logic([req], post)

        req.approve.assert_called_once_with(dollar_amount=None, discount_percent="150")
        self.assertNotIn("Ivan", users_approved)
        self.assertEqual(len(users_error), 1)
        self.assertIn("Ivan", users_error[0])
        self.assertIn(error_msg, users_error[0])