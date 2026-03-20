import pytest
from django.contrib.auth.models import Group
from esp.program.modules.handlers.usergroupmodule import UserGroupModule
from esp.users.models import ESPUser


@pytest.mark.django_db
def test_create_new_group_and_add_users():
    user1 = ESPUser.objects.create(username="user1")
    user2 = ESPUser.objects.create(username="user2")

    class MockFilter:
        def getList(self, model):
            return ESPUser.objects.filter(id__in=[user1.id, user2.id])

    message = UserGroupModule.updateGroup(MockFilter(), "new_group")

    group = Group.objects.get(name="new_group")

    assert group.user_set.count() == 2
    assert "has been created" in message
    assert "2 new users have been added" in message


@pytest.mark.django_db
def test_add_users_to_existing_group():
    user = ESPUser.objects.create(username="user3")
    group = Group.objects.create(name="existing_group")

    class MockFilter:
        def getList(self, model):
            return ESPUser.objects.filter(id=user.id)

    message = UserGroupModule.updateGroup(MockFilter(), "existing_group")

    assert user in group.user_set.all()
    assert "1 new users have been added" in message


@pytest.mark.django_db
def test_clean_group_replaces_users():
    user1 = ESPUser.objects.create(username="user4")
    user2 = ESPUser.objects.create(username="user5")

    group = Group.objects.create(name="clean_group")
    group.user_set.add(user1)

    class MockFilter:
        def getList(self, model):
            return ESPUser.objects.filter(id=user2.id)

    message = UserGroupModule.updateGroup(MockFilter(), "clean_group", clean=True)

    users = group.user_set.all()

    assert user1 not in users
    assert user2 in users
    assert "removed from user group" in message


@pytest.mark.django_db
def test_no_users_raises_error():
    class MockFilter:
        def getList(self, model):
            return ESPUser.objects.none()

    with pytest.raises(Exception) as exc:
        UserGroupModule.updateGroup(MockFilter(), "test_group")

    assert "did not match any users" in str(exc.value)


@pytest.mark.django_db
def test_no_duplicate_addition():
    user = ESPUser.objects.create(username="user6")
    group = Group.objects.create(name="dup_group")
    group.user_set.add(user)

    class MockFilter:
        def getList(self, model):
            return ESPUser.objects.filter(id=user.id)

    UserGroupModule.updateGroup(MockFilter(), "dup_group")

    # Ensure no duplicate
    assert group.user_set.count() == 1


@pytest.mark.django_db
def test_log_message_output():
    user = ESPUser.objects.create(username="user7")

    class MockFilter:
        def getList(self, model):
            return ESPUser.objects.filter(id=user.id)

    message = UserGroupModule.updateGroup(MockFilter(), "log_group")

    assert "added to user group" in message
    assert "now has" in message