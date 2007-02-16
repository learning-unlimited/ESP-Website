from django.db import models
from esp.datatree.models import DataTree
from esp.program.modules.base import ProgramModuleObj

class ClassRegModuleInfo(models.Model):
    module       = models.ForeignKey(ProgramModuleObj)
    allow_coteach        = models.BooleanField(blank=True, null=True)
    display_times        = models.BooleanField(blank=True, null=True)
    times_selectmultiple = models.BooleanField(blank=True, null=True)
    class_min_size       = models.IntegerField(blank=True, null=True)
    class_max_size       = models.IntegerField(blank=True, null=True)
    class_size_step      = models.IntegerField(blank=True, null=True)
    director_email       = models.CharField(maxlength=64, blank=True, null=True)
    class_durations       = models.CharField(maxlength=128, blank=True, null=True)
    teacher_class_noedit = models.DateTimeField(blank=True, null=True)
    
    class_durations_any = models.BooleanField(blank=True, null=True)
    def __str__(self):
        return 'Class Reg Ext. for %s' % str(self.module)
    
    class Admin:
        pass
    


class CreditCardModuleInfo(models.Model):
    module = models.ForeignKey(ProgramModuleObj)
    base_cost        = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return 'Credit Card Ext. for %s' % str(self.module)

    class Admin:
        pass


class SATPrepTeacherModuleInfo(models.Model):
    from esp.users.models import User
    from esp.program.models import Program

    """ Module that links a user with a program and has SATPrep teacher info"""
    SAT_SUBJECTS = (
        ('M', 'Math'),
        ('V', 'Verbal'),
        ('W', 'Writing')
        )

    sat_math = models.PositiveIntegerField(blank=True, null=True)
    sat_writ = models.PositiveIntegerField(blank=True, null=True)
    sat_verb = models.PositiveIntegerField(blank=True, null=True)

    mitid    = models.PositiveIntegerField(blank=True, null=True)

    subject  = models.CharField(maxlength=32, choices = SAT_SUBJECTS)

    user     = models.ForeignKey(User,blank=True, null=True)
    program  = models.ForeignKey(Program,blank=True, null=True)
   
    def __str__(self):
        return 'SATPrep Information for teacher %s in %s' % \
                 (str(self.user), str(self.program))

    class Admin:
        pass

    @staticmethod
    def subjects():
        return SATPrepTeacherModuleInfo.SAT_SUBJECTS


