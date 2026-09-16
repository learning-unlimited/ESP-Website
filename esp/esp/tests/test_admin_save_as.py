"""
Tests for admin object duplication ("Save as new").
Source: esp/esp/admin.py

ESPAdminSite turns Django's `save_as` on for every registered ModelAdmin, so
these tests pin down which admins opt out and check that the ones that don't
can actually save the duplicate they offer.
"""
from django.test import RequestFactory

from esp.accounting.models import CybersourcePostback
from esp.admin import admin_site, autodiscover
from esp.application.models import (FormstackAppSettings,
                                    FormstackStudentClassApp,
                                    FormstackStudentProgramApp)
from esp.dbmail.models import TextOfEmail
from esp.program.models import (FinancialAidRequest, StudentApplication,
                                StudentAppResponse, StudentAppReview)
from esp.qsd.models import QuasiStaticData
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import ESPUser, GradeChangeRequest
from esp.utils.models import TemplateOverride

#   Admins that turn "Save as new" off; see their comments for why.
NOT_DUPLICABLE = {
    CybersourcePostback,
    ESPUser,
    FinancialAidRequest,
    FormstackAppSettings,
    FormstackStudentClassApp,
    FormstackStudentProgramApp,
    GradeChangeRequest,
    StudentApplication,
    StudentAppResponse,
    StudentAppReview,
    TextOfEmail,
}

#   Required fields that are kept off the form on purpose because something
#   else fills them in on the way to the database.
FILLED_IN_ON_SAVE = {
    QuasiStaticData: {'author'},        # QuasiStaticDataAdmin.save_model
    TemplateOverride: {'version'},      # TemplateOverride.save
}


class AllowAllUser:
    """Stands in for a superuser without touching the database."""
    is_active = True
    is_staff = True
    is_superuser = True

    def has_perm(self, perm, obj=None):
        return True


def required_db_fields(model):
    """Names of the fields the database will reject if the form omits them."""
    names = set()
    for field in model._meta.concrete_fields:
        if field.primary_key or field.null or field.has_default():
            continue
        if field.empty_strings_allowed:
            #   An omitted CharField/TextField saves as '', which is fine.
            continue
        if getattr(field, 'auto_now', False) or getattr(field, 'auto_now_add', False):
            continue
        names.add(field.name)
    return names


class AdminSaveAsTest(TestCase):

    def setUp(self):
        super().setUp()
        #   The registry is filled by esp.urls, which the tests may not have
        #   imported yet.  Importing the admin modules twice is a no-op.
        autodiscover(admin_site)
        self.request = RequestFactory().get('/')
        self.request.user = AllowAllUser()

    def test_admins_are_registered(self):
        self.assertGreater(len(admin_site._registry), 1)

    def test_save_as_is_on_unless_the_admin_opts_out(self):
        for model, model_admin in admin_site._registry.items():
            with self.subTest(model=model.__name__):
                self.assertEqual(model_admin.save_as, model not in NOT_DUPLICABLE)

    def test_duplicates_can_be_saved(self):
        """Every field the database requires must be on the add form.

        Django's "Save as new" builds the copy from the add form alone, so a
        required field that is readonly, excluded or `editable=False` turns
        the button into an IntegrityError.
        """
        for model, model_admin in admin_site._registry.items():
            if not model_admin.save_as:
                continue
            if not model_admin.has_add_permission(self.request):
                continue
            with self.subTest(model=model.__name__):
                form = model_admin.get_form(self.request, obj=None, change=False)
                missing = required_db_fields(model) - set(form.base_fields)
                self.assertEqual(missing - FILLED_IN_ON_SAVE.get(model, set()), set())
