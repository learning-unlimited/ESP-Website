from django.test import TestCase
from django.contrib.auth.models import User
from esp.tagdict.models import Tag


class TagTest(TestCase):
    def testTagGetSet(self):
        """
        Test that the get and set methods for tags, work.
        Note that at this time, I assume that GenericForeignKeys and the caching API
        work as specified, and are invoked correctly on this class.
        """
        # Dump any existing Tag cache
        Tag.getTag.delete_all()

        self.failIf(bool(Tag.getTag("test")), "Retrieved a tag for key 'test' but we haven't set one yet!")
        self.failIf(Tag.getTag("test"), "getTag() created a retrievable value for key 'test'!")

        Tag.setTag("test", value="frobbed")
        self.assertEqual(Tag.getTag("test"), "frobbed", "Failed to set tag 'test' to value 'frobbed'!")
        self.assertEqual(Tag.getTag("test"), "frobbed", "Tag was created, but didn't stick!")

        Tag.unSetTag("test")

        self.failIf(Tag.getTag("test"), "Retrieved a tag for key 'test' but we just deleted it!")
        self.failIf(Tag.getTag("test"), "unSetTag() deletes don't appear to be persistent!")

        Tag.setTag("test")
        self.failUnless(Tag.getTag("test"), "Error:  Setting a tag with an unspecified value must yield a tag whose value evaluates to True!")

        user, created = User.objects.get_or_create(username="TestUser123", email="test@example.com", password="")

        self.failIf(Tag.getTag("test", user), "Retrieved a tag for key 'test' target '%s', but we haven't set one yet!" % (user))
        Tag.setTag("test", user, "frobbed again")
        self.assertEqual(Tag.getTag("test", user), "frobbed again")
        Tag.setTag("test", user)
        self.assertEqual(Tag.getTag("test", user), Tag.EMPTY_TAG)
        Tag.unSetTag("test", user)
        self.failIf(Tag.getTag("test", user), "unSetTag() didn't work for per-row tags!")


                   
        


