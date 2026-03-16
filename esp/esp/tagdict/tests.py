from django.test import TestCase
from django.contrib.auth.models import User
from esp.tagdict import all_global_tags, all_program_tags
from esp.tagdict.models import Tag
from esp.program.tests import ProgramFrameworkTest

# Make test-only tags not raise warnings
all_global_tags['test'] = {
    'is_boolean': False,
    'help_text': '',
    'default': None,
    'category': 'manage',
    'is_setting': True,
}
all_program_tags['test'] = {
    'is_boolean': False,
    'help_text': '',
    'default': None,
    'category': 'manage',
    'is_setting': True,
}
all_global_tags['test_bool'] = {
    'is_boolean': True,
    'help_text': '',
    'default': False,
    'category': 'manage',
    'is_setting': True,
}
all_program_tags['test_bool'] = {
    'is_boolean': True,
    'help_text': '',
    'default': False,
    'category': 'manage',
    'is_setting': True,
}

class TagTest(TestCase):
    def testTagGetSet(self):
        """
        Test that the get and set methods for tags, work.
        Note that at this time, I assume that GenericForeignKeys work
        and are invoked correctly on this class.
        """
        # Dump any existing Tag cache
        Tag._getTag.delete_all()

        self.assertFalse(bool(Tag.getTag("test")), "Retrieved a tag for key 'test' but we haven't set one yet!")
        self.assertFalse(Tag.getTag("test"), "getTag() created a retrievable value for key 'test'!")
        self.assertEqual(Tag.getTag("test",default="the default"),"the default")
        self.assertEqual(Tag.getTag("test",default="the default"),"the default")

        Tag.setTag("test", value="frobbed")
        self.assertEqual(Tag.getTag("test"), "frobbed", "Failed to set tag 'test' to value 'frobbed'!")
        self.assertEqual(Tag.getTag("test"), "frobbed", "Tag was created, but didn't stick!")
        self.assertEqual(Tag.getTag("test",default="the default"), "frobbed", "Defaulting is borked!")
        self.assertEqual(Tag.getTag("test",default="the default"), "frobbed", "Defaulting is borked!")

        Tag.unSetTag("test")

        self.assertFalse(Tag.getTag("test"), "Retrieved a tag for key 'test' but we just deleted it!")
        self.assertFalse(Tag.getTag("test"), "unSetTag() deletes don't appear to be persistent!")
        self.assertEqual(Tag.getTag("test",default="the default"),"the default")
        self.assertEqual(Tag.getTag("test",default="the default"),"the default")

        Tag.setTag("test")
        self.assertTrue(Tag.getTag("test"), "Error:  Setting a tag with an unspecified value must yield a tag whose value evaluates to True!")
        self.assertNotEqual(Tag.getTag("test",default="the default"),"the default","If the tag is set, even to EMPTY_TAG, we shouldn't return the default.")

    def testTagWithTarget(self):
        '''Test getting and setting of tags with targets.'''
        # Delete any existing tags that might interfere
        Tag.objects.filter(key="test").delete()
        # Dump any existing Tag cache
        Tag._getTag.delete_all()

        user, created = User.objects.get_or_create(username="TestUser123", email="test@example.com", password="")

        self.assertFalse(Tag.getTag("test", user), "Retrieved a tag for key 'test' target '%s', but we haven't set one yet!" % (user))
        Tag.setTag("test", user, "frobbed again")
        self.assertEqual(Tag.getTag("test", user), "frobbed again")
        Tag.setTag("test", user)
        self.assertEqual(Tag.getTag("test", user), Tag.EMPTY_TAG)
        Tag.unSetTag("test", user)
        self.assertFalse(Tag.getTag("test", user), "unSetTag() didn't work for per-row tags!")

    def testTagCaching(self):
        '''Test that tag values are being cached.'''
        # Delete any existing tags that might interfere
        Tag.objects.filter(key="test").delete()
        # Dump any existing Tag cache
        Tag._getTag.delete_all()

        user1, created = User.objects.get_or_create(username="TestUser1", email="test1@example.com", password="")
        user2, created = User.objects.get_or_create(username="TestUser2", email="test2@example.com", password="")

        for target in [None,user1,user2]:
            self.assertFalse(Tag.getTag("test",target=target))
            with self.assertNumQueries(0):
                self.assertFalse(Tag.getTag("test",target=target))
                self.assertFalse(Tag.getTag("test",target=target))





        Tag.setTag("test",value="tag value")

        for target in [user1,user2]:
            self.assertFalse(Tag.getTag("test",target=target)) #remove after Issue #866 is fixed
            with self.assertNumQueries(0):
                self.assertFalse(Tag.getTag("test",target=target))
                self.assertFalse(Tag.getTag("test",target=target))

        self.assertEqual(Tag.getTag("test"),"tag value")
        with self.assertNumQueries(0):
            self.assertEqual(Tag.getTag("test"),"tag value")
            self.assertEqual(Tag.getTag("test"),"tag value")

        for target in [user1,user2]:
            self.assertFalse(Tag.getTag("test",target=target)) #remove after Issue #866 is fixed
            with self.assertNumQueries(0):
                self.assertFalse(Tag.getTag("test",target=target))
                self.assertFalse(Tag.getTag("test",target=target))




        Tag.setTag("test",value="tag value 2")

        for target in [user1,user2]:
            self.assertFalse(Tag.getTag("test",target=target)) #remove after Issue #866 is fixed
            with self.assertNumQueries(0):
                self.assertFalse(Tag.getTag("test",target=target))
                self.assertFalse(Tag.getTag("test",target=target))

        self.assertEqual(Tag.getTag("test"),"tag value 2")
        with self.assertNumQueries(0):
            self.assertEqual(Tag.getTag("test"),"tag value 2")
            self.assertEqual(Tag.getTag("test"),"tag value 2")

        for target in [user1,user2]:
            self.assertFalse(Tag.getTag("test",target=target)) #remove after Issue #866 is fixed
            with self.assertNumQueries(0):
                self.assertFalse(Tag.getTag("test",target=target))
                self.assertFalse(Tag.getTag("test",target=target))



        Tag.setTag("test",target=user1,value="tag value user1")

        self.assertFalse(Tag.getTag("test",target=user2)) #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertFalse(Tag.getTag("test",target=user2))
            self.assertFalse(Tag.getTag("test",target=user2))

        self.assertEqual(Tag.getTag("test"),"tag value 2") #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertEqual(Tag.getTag("test"),"tag value 2")
            self.assertEqual(Tag.getTag("test"),"tag value 2")

        self.assertEqual(Tag.getTag("test",target=user1),"tag value user1")
        with self.assertNumQueries(0):
            self.assertEqual(Tag.getTag("test",target=user1),"tag value user1")
            self.assertEqual(Tag.getTag("test",target=user1),"tag value user1")

        self.assertEqual(Tag.getTag("test"),"tag value 2") #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertEqual(Tag.getTag("test"),"tag value 2")
            self.assertEqual(Tag.getTag("test"),"tag value 2")

        self.assertFalse(Tag.getTag("test",target=user2)) #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertFalse(Tag.getTag("test",target=user2))
            self.assertFalse(Tag.getTag("test",target=user2))



        Tag.unSetTag("test")

        self.assertEqual(Tag.getTag("test",target=user1),"tag value user1") #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertEqual(Tag.getTag("test",target=user1),"tag value user1")
            self.assertEqual(Tag.getTag("test",target=user1),"tag value user1")

        self.assertFalse(Tag.getTag("test",target=user2)) #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertFalse(Tag.getTag("test",target=user2))
            self.assertFalse(Tag.getTag("test",target=user2))

        self.assertFalse(Tag.getTag("test"))
        with self.assertNumQueries(0):
            self.assertFalse(Tag.getTag("test"))
            self.assertFalse(Tag.getTag("test"))

        self.assertEqual(Tag.getTag("test",target=user1),"tag value user1") #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertEqual(Tag.getTag("test",target=user1),"tag value user1")
            self.assertEqual(Tag.getTag("test",target=user1),"tag value user1")

        self.assertFalse(Tag.getTag("test",target=user2)) #remove after Issue #866 is fixed
        with self.assertNumQueries(0):
            self.assertFalse(Tag.getTag("test",target=user2))
            self.assertFalse(Tag.getTag("test",target=user2))

class ProgramTagTest(ProgramFrameworkTest):
    def testProgramTag(self):
        '''Test the logic of getProgramTag in a bunch of different conditions.'''

        # Delete any existing tags that might interfere
        Tag.objects.filter(key="test").delete()
        # Dump any existing Tag cache
        Tag._getTag.delete_all()

        #Caching is hard, so what the hell, let's run every assertion twice.
        self.assertFalse(Tag.getProgramTag("test",program=self.program))
        self.assertFalse(Tag.getProgramTag("test",program=self.program))
        self.assertFalse(Tag.getProgramTag("test",program=None))
        self.assertFalse(Tag.getProgramTag("test",program=None))
        self.assertEqual(Tag.getProgramTag("test",program=self.program,default="the default"),"the default")
        self.assertEqual(Tag.getProgramTag("test",program=self.program,default="the default"),"the default")
        self.assertEqual(Tag.getProgramTag("test",program=None,default="the default"),"the default")
        self.assertEqual(Tag.getProgramTag("test",program=None,default="the default"),"the default")


        # Set the program-specific tag
        Tag.setTag("test",target=self.program,value="program tag value")

        self.assertFalse(Tag.getProgramTag("test",program=None))
        self.assertFalse(Tag.getProgramTag("test",program=None))
        self.assertEqual(Tag.getProgramTag("test",program=None,default="the default"),"the default")
        self.assertEqual(Tag.getProgramTag("test",program=None,default="the default"),"the default")
        self.assertEqual(Tag.getProgramTag("test",program=self.program),"program tag value")
        self.assertEqual(Tag.getProgramTag("test",program=self.program),"program tag value")
        self.assertEqual(Tag.getProgramTag("test",program=self.program,default="the default"),"program tag value")
        self.assertEqual(Tag.getProgramTag("test",program=self.program,default="the default"),"program tag value")


        # Now set the general tag
        Tag.setTag("test",target=None,value="general tag value")

        self.assertEqual(Tag.getProgramTag("test",program=None),"general tag value")
        self.assertEqual(Tag.getProgramTag("test",program=None),"general tag value")
        self.assertEqual(Tag.getProgramTag("test",program=None,default="the default"),"general tag value")
        self.assertEqual(Tag.getProgramTag("test",program=None,default="the default"),"general tag value")
        self.assertEqual(Tag.getProgramTag("test",program=self.program),"program tag value")
        self.assertEqual(Tag.getProgramTag("test",program=self.program),"program tag value")
        self.assertEqual(Tag.getProgramTag("test",program=self.program,default="the default"),"program tag value")
        self.assertEqual(Tag.getProgramTag("test",program=self.program,default="the default"),"program tag value")


        # Now unset the program-specific tag
        Tag.unSetTag("test",target=self.program)

        self.assertEqual(Tag.getProgramTag("test",program=None),"general tag value")
        self.assertEqual(Tag.getProgramTag("test",program=None),"general tag value")
        self.assertEqual(Tag.getProgramTag("test",program=None,default="the default"),"general tag value")
        self.assertEqual(Tag.getProgramTag("test",program=None,default="the default"),"general tag value")
        self.assertEqual(Tag.getProgramTag("test",program=self.program),"general tag value")
        self.assertEqual(Tag.getProgramTag("test",program=self.program),"general tag value")
        self.assertEqual(Tag.getProgramTag("test",program=self.program,default="the default"),"general tag value")
        self.assertEqual(Tag.getProgramTag("test",program=self.program,default="the default"),"general tag value")

        #just to clean up
        Tag.unSetTag("test",target=None)

        self.assertFalse(Tag.getProgramTag("test",program=self.program))
        self.assertFalse(Tag.getProgramTag("test",program=self.program))
        self.assertFalse(Tag.getProgramTag("test",program=None))
        self.assertFalse(Tag.getProgramTag("test",program=None))
        self.assertEqual(Tag.getProgramTag("test",program=self.program,default="the default"),"the default")
        self.assertEqual(Tag.getProgramTag("test",program=self.program,default="the default"),"the default")
        self.assertEqual(Tag.getProgramTag("test",program=None,default="the default"),"the default")
        self.assertEqual(Tag.getProgramTag("test",program=None,default="the default"),"the default")

    def testBooleanTag(self):
        '''Test the logic of getBooleanTag in a bunch of different conditions, assuming that the underlying getProgramTag works.'''
        # Dump any existing Tag cache
        Tag._getTag.delete_all()

        self.assertFalse(Tag.getBooleanTag("test_bool"))
        self.assertFalse(Tag.getBooleanTag("test_bool"))
        self.assertFalse(Tag.getBooleanTag("test_bool", program=None))
        self.assertFalse(Tag.getBooleanTag("test_bool", program=None))
        self.assertFalse(Tag.getBooleanTag("test_bool", program=self.program))
        self.assertFalse(Tag.getBooleanTag("test_bool", program=self.program))
        for b in [True,False]:
            self.assertEqual(Tag.getBooleanTag("test_bool",default=b),b)
            self.assertEqual(Tag.getBooleanTag("test_bool",default=b),b)
            self.assertEqual(Tag.getBooleanTag("test_bool",program=None,default=b),b)
            self.assertEqual(Tag.getBooleanTag("test_bool",program=None,default=b),b)
            self.assertEqual(Tag.getBooleanTag("test_bool",program=self.program,default=b),b)
            self.assertEqual(Tag.getBooleanTag("test_bool",program=self.program,default=b),b)

        for true_val in [True,"True","true","1",1]:
            Tag.setTag("test_bool",target=self.program,value=true_val)

            self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program), True)
            self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program), True)
            for b in [True,False]:
                self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program, default=b), True)
                self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program, default=b), True)

        for false_val in [False,"False","false","0",0]:
            Tag.setTag("test_bool",target=self.program,value=false_val)

            self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program), False)
            self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program), False)
            for b in [True,False]:
                self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program, default=b), False)
                self.assertEqual(Tag.getBooleanTag("test_bool", program=self.program, default=b), False)
