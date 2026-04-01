import json
from esp.tests.util import CacheFlushTestCase as TestCase
from esp.program.models import Program, ClassSubject, ClassCategories
from esp.program.models.flags import AutoClassFlagRule, ClassFlagType, ClassFlag
from esp.users.models import ESPUser

class AutoClassFlagTest(TestCase):
    def setUp(self):
        super().setUp()
        self.program = Program.objects.create(
            name="Test Program",
            url="testprog",
            grade_min=7,
            grade_max=12
        )
        self.category = ClassCategories.objects.create(
            symbol="S",
            category="Science"
        )
        self.system_user = ESPUser.objects.create(
            username="systemadmin",
            is_staff=True,
            is_superuser=True
        )
        self.flag_type = ClassFlagType.objects.create(
            name="Test Flag"
        )
        self.program.flag_types.add(self.flag_type)
        # Create a rule: Title starts with "Trigger"
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
                    "operator": "istartswith",
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
