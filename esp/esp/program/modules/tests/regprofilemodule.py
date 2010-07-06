from datetime import datetime, timedelta
from esp.program.tests import ProgramFrameworkTest

class RegProfileModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        from esp.datatree.models import GetNode
        from esp.program.models import Program
        from esp.program.modules.base import ProgramModule, ProgramModuleObj

        # Set up the program -- we want to be sure of these parameters
        kwargs.update({'num_students': 2,})
        super(RegProfileModuleTest, self).setUp(*args, **kwargs)

        # Get and remember the instance of this module
        m = ProgramModule.objects.get(handler='RegProfileModule', module_type='learn')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, m)

        self.dummyprog = Program.objects.get(anchor = GetNode("Q/Programs/Dummy_Programs/Profile_Storage"))

    def runTest(self):
        from esp.program.models import RegistrationProfile

        # Check that the people start out without profiles
        # We'll probably need to be a little more careful about how we set
        # the ProgramModuleObj's user if we ever cache isCompleted().
        for student in self.students:
            self.moduleobj.user = student
            self.failUnless( not self.moduleobj.isCompleted(), "The profile should be incomplete at first." )

        # First student: Test copying of sufficiently recent profiles
        self.moduleobj.user = self.students[0]
        prof = self.students[0].getLastProfile()
        prof.program = self.dummyprog
        prof.save()
        self.failUnless( self.students[0].registrationprofile_set.count() >= 1, "Profile failed to save." )
        self.failUnless( self.students[0].registrationprofile_set.count() <= 1, "Too many profiles." )
        self.failUnless( self.moduleobj.isCompleted(), "Profile failed to copy." )
        self.failUnless( self.students[0].registrationprofile_set.count() >= 2, "Copy failed to save." )
        self.failUnless( self.students[0].registrationprofile_set.count() <= 2, "Too many profiles." )

        # Second student: Test non-auto-saving of sufficiently old profiles
        self.moduleobj.user = self.students[1]
        prof = self.students[1].getLastProfile()
        prof.program = self.dummyprog
        # HACK -- save properly to dump the appropriate cache.
        # Then save sneakily so that we can override the timestamp.
        prof.save()
        prof.last_ts = datetime.now() - timedelta(10)
        super(RegistrationProfile, prof).save()
        # Continue testing
        self.failUnless( self.students[1].registrationprofile_set.count() >= 1, "Profile failed to save." )
        self.failUnless( self.students[1].registrationprofile_set.count() <= 1, "Too many profiles." )
        self.failUnless( not self.moduleobj.isCompleted(), "Profile too old but accepted anyway." )
        self.failUnless( self.students[1].registrationprofile_set.count() <= 1, "Too many profiles." )
