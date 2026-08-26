import json
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.program.models import (
    Program, ClassSubject, ClassFlagType, ClassFlag, AutoClassFlagRule,
    ESPUser, ClassCategories
)
from esp.program.modules.module_ext import ClassRegModuleInfo
from esp.program.modules.handlers.classsearchmodule import ClassSearchModule
from esp.middleware.threadlocalrequest import clear_current_request

class AutoClassFlagTest(TestCase):
    def setUp(self):
        super().setUp()
        clear_current_request()
        self.program = Program.objects.create(
            name="Test Program",
            url="testprog",
            grade_min=7,
            grade_max=12
        )
        # Create required ClassRegModuleInfo for ClassSearchModule to function
        ClassRegModuleInfo.objects.create(program=self.program)

        self.category = ClassCategories.objects.create(
            symbol="S",
            category="Science"
        )
        self.system_user = ESPUser.objects.create_superuser(
            username="systemadmin",
            email="admin@example.com",
            password="password123"
        )
        self.flag_type = ClassFlagType.objects.create(
            name="Test Flag"
        )
        self.program.flag_types.add(self.flag_type)
        # Create a rule: Title contains "Trigger"
        # This uses the QueryBuilder client format expected by ClassSearchModule /
        # QueryBuilder.as_queryset: groups use "filter": "and"/"or" with "values"
        # containing child filter objects.
        self.rule_data = {
            "filter": "and",
            "negated": False,
            "values": [
                {
                    "filter": "title",
                    "negated": False,
                    "values": ["Trigger"],
                }
            ]
        }
        self.rule = AutoClassFlagRule.objects.create(
            program=self.program,
            flag_type=self.flag_type,
            rule_data=json.dumps(self.rule_data),
            comment="Automatically flagged!"
        )

    def _get_matching_queryset(self):
        """Return the queryset of classes matching self.rule."""
        module = ClassSearchModule(program=self.program)
        qb = module.query_builder()
        decoded = json.loads(self.rule.rule_data)
        return qb.as_queryset(decoded).distinct()

    def test_auto_flag_triggered(self):
        """Test that the flag is added when the class matches the rule."""
        cls = ClassSubject.objects.create(
            title="Trigger Class",
            parent_program=self.program,
            category=self.category,
            grade_min=7,
            grade_max=12
        )
        # Check if flag was added
        self.assertTrue(ClassFlag.objects.filter(subject=cls, flag_type=self.flag_type).exists())
        flag = ClassFlag.objects.get(subject=cls, flag_type=self.flag_type)
        self.assertEqual(flag.comment, "Automatically flagged!")

    def test_auto_flag_not_triggered(self):
        """Test that the flag is NOT added when the class does NOT match the rule."""
        cls = ClassSubject.objects.create(
            title="Normal Class",
            parent_program=self.program,
            category=self.category,
            grade_min=7,
            grade_max=12
        )
        # Check if flag was added
        self.assertFalse(ClassFlag.objects.filter(subject=cls, flag_type=self.flag_type).exists())

    def test_apply_existing_classes_flagged(self):
        """Test that apply_existing bulk-applies flags to matching classes."""
        # Create classes BEFORE the rule would apply
        matching = ClassSubject.objects.create(
            title="Trigger Existing",
            parent_program=self.program,
            category=self.category,
            grade_min=7,
            grade_max=12
        )
        # The signal will auto-flag this because self.rule already exists,
        # so clear it to simulate the "create rule with apply_existing" flow
        ClassFlag.objects.filter(subject=matching).delete()
        self.assertFalse(
            ClassFlag.objects.filter(subject=matching, flag_type=self.flag_type).exists()
        )

        self.rule.apply_to_queryset(self._get_matching_queryset(), user=self.system_user)

        self.assertTrue(
            ClassFlag.objects.filter(subject=matching, flag_type=self.flag_type).exists()
        )

    def test_apply_existing_non_matching_not_flagged(self):
        """Test that apply_existing does NOT flag classes that don't match."""
        non_matching = ClassSubject.objects.create(
            title="Safe Class",
            parent_program=self.program,
            category=self.category,
            grade_min=7,
            grade_max=12
        )
        # Clear any flags (signal shouldn't have added any, but be safe)
        ClassFlag.objects.filter(subject=non_matching).delete()

        self.rule.apply_to_queryset(self._get_matching_queryset(), user=self.system_user)

        self.assertFalse(
            ClassFlag.objects.filter(subject=non_matching, flag_type=self.flag_type).exists()
        )
