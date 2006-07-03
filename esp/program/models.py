from django.db import models
from django.contrib.auth.models import User
from esp.calendar.models import Series, Event

# Create your models here.

class ProgramType(models.Model):
    """ A list of all possible types of program, such as HSSP, Splash, Delve, etc. """
    program_name = models.TextField()

    def __str__(self):
	    return self.program_name

    class Admin:
        pass

class Program(models.Model):
    """ An ESP Program, such as HSSP, Splash, Delve, etc. """
    programSchedule = models.ForeignKey(Series) # Series containing all events in the program, probably including an event that spans the full duration of the program, to represent this program
    programType = models.ForeignKey(ProgramType)
    programIdentifier = models.TextField(blank=True) # Human-readable, per-instance identifier.  For example, for HSSP, this might be "Summer 2006".  This doesn't need to be unique, nor even non-blank.

    class Admin:
        pass

class ClassCategories(models.Model):
    """ A list of all possible categories for an ESP class

    Categories include 'Mathematics', 'Science', 'Zocial Zciences', etc.
    """
    category = models.TextField()

    class Admin:
        pass

class EquipmentType(models.Model):
    """ A type of equipment that is available for classes to use

    Equipment types include projectors, classrooms with desks, Athena labs, and the like """
    equipment = models.TextField() # Human-readable name of the element of equipment
    numAvailable = models.IntegerField() # Number of this item of equipment owned by ESP

    class Admin:
        pass

class Class(models.Model):
    """ A Class, as taught as part of an ESP program """
    title = models.TextField()
    category = models.ForeignKey(ClassCategories)
    teachers = models.ManyToManyField(User)
    class_info = models.TextField()
    equipment_needed = models.ManyToManyField(EquipmentType)
    message_for_directors = models.TextField()
    grade_min = models.IntegerField()
    grade_max = models.IntegerField()
    class_size_min = models.IntegerField()
    class_size_max = models.IntegerField()
    parent_program = models.ForeignKey(Program)
    schedule = models.ForeignKey(Series)

    class Admin:
        pass
