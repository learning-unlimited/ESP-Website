from django.contrib.auth.models import Group
from django.test import TestCase
from esp.program.modules.handlers.usergroupmodule import UserGroupModule
from esp.users.models import ESPUser


class UserGroupModuleTests(TestCase):

    def test_create_new_group_and_add_users(self):
        user1 = ESPUser.objects.create(username="user1")
        user2 = ESPUser.objects.create(username="user2")

        class MockFilter:
            def getList(self, model):
                return ESPUser.objects.filter(id__in=[user1.id, user2.id])

        message = UserGroupModule.updateGroup(MockFilter(), "new_group")
        group = Group.objects.get(name="new_group")

        self.assertEqual(group.user_set.count(), 2)
        self.assertIn("new_group", message)
        self.assertIn("added", message)

    def test_add_users_to_existing_group(self):
        user = ESPUser.objects.create(username="user3")
        group = Group.objects.create(name="existing_group")

        class MockFilter:
            def getList(self, model):
                return ESPUser.objects.filter(id=user.id)

        message = UserGroupModule.updateGroup(MockFilter(), "existing_group")

        self.assertIn(user, group.user_set.all())
        self.assertIn("existing_group", message)
        self.assertIn("added", message)

    def test_clean_group_replaces_users(self):
        user1 = ESPUser.objects.create(username="user4")
        user2 = ESPUser.objects.create(username="user5")

        group = Group.objects.create(name="clean_group")
        group.user_set.add(user1)

        class MockFilter:
            def getList(self, model):
                return ESPUser.objects.filter(id=user2.id)

        message = UserGroupModule.updateGroup(MockFilter(), "clean_group", clean=True)

        users = group.user_set.all()

        self.assertNotIn(user1, users)
        self.assertIn(user2, users)
        self.assertIn("removed", message)

    def test_no_users_raises_error(self):
        class MockFilter:
            def getList(self, model):
                return ESPUser.objects.none()

        with self.assertRaises(Exception) as context:
            UserGroupModule.updateGroup(MockFilter(), "test_group")

        self.assertIn("did not match any users", str(context.exception))

    def test_no_duplicate_addition(self):
        user = ESPUser.objects.create(username="user6")
        group = Group.objects.create(name="dup_group")
        group.user_set.add(user)

        class MockFilter:
            def getList(self, model):
                return ESPUser.objects.filter(id=user.id)

        UserGroupModule.updateGroup(MockFilter(), "dup_group")

        self.assertEqual(group.user_set.count(), 1)

    def test_log_message_output(self):
        user = ESPUser.objects.create(username="user7")

        class MockFilter:
            def getList(self, model):
                return ESPUser.objects.filter(id=user.id)

        message = UserGroupModule.updateGroup(MockFilter(), "log_group")

        self.assertIn("log_group", message)
        self.assertIn("added", message)
        self.assertIn("now has", message)