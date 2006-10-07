from django.db import models
from django.contrib.auth.models import User
from esp.calendar.models import Event
from esp.datatree.models import DataTree, GetNode
from esp.users.models import UserBit, ContactInfo
from esp.lib.markdown import markdown
from esp.qsd.models import QuasiStaticData

# Create your models here.

class Program(models.Model):
    """ An ESP Program, such as HSSP Summer 2006, Splash Fall 2006, Delve 2005, etc. """
    anchor = models.ForeignKey(DataTree) # Series containing all events in the program, probably including an event that spans the full duration of the program, to represent this program

    def url(self):
        str_array = self.anchor.tree_encode()
        return '/'.join(str_array[2:])
    
    def __str__(self):
        return str(self.anchor.parent.friendly_name) + ' ' + str(self.anchor.friendly_name)

    def parent(self):
	    return anchor.parent

    class Admin:
        pass
    
    @staticmethod
    def find_by_perms(user, verb):
    	""" Fetch a list of relevant programs for a given user and verb """
	return UserBit.find_by_anchor_perms(Program,user,verb)

class ClassCategories(models.Model):
    """ A list of all possible categories for an ESP class

    Categories include 'Mathematics', 'Science', 'Zocial Zciences', etc.
    """
    category = models.TextField()

    def __str__(self):
        return str(self.category)

    class Admin:
        pass

# FIXME: The Class object should use the permissions system to control
# which grades (Q/Community/6_12/*) are permitted to join the class, though
# the UI should make it as clean as two numbers, at least initially.
class Class(models.Model):
	""" A Class, as taught as part of an ESP program """
	anchor = models.ForeignKey(DataTree)
	parent_program = models.ForeignKey(Program)
	# title drawn from anchor.friendly_name
	# class number drawn from anchor.name
	category = models.ForeignKey(ClassCategories)
	# teachers are drawn from permissions table
	class_info = models.TextField(blank=True)
	message_for_directors = models.TextField(blank=True)
	grade_min = models.IntegerField()
	grade_max = models.IntegerField()
	class_size_min = models.IntegerField()
	class_size_max = models.IntegerField()
	schedule = models.TextField(blank=True)
	event_template = models.ForeignKey(DataTree, related_name='class_event_template_set')
	enrollment = models.IntegerField()

	def got_qsd(self):
		return (QuasiStaticData.objects.filter(path = self.anchor).count() > 0)

        def PopulateEvents(self):
            """ Given this instance's event_template, generate a series of events that define this class's schedule """
            for e in self.event_template.event_set.all():
                newevent = Event()
                newevent.start = e.start
                newevent.end = e.end
                newevent.short_description = e.short_description
                newevent.description = e.description.replace('[event]', e.anchor.friendly_name) # Allow for the insertion of event names, so that the templates are less generic/nonspecific
                newevent.event_type = e.event_type
                newevent.anchor = self.anchor
                newevent.save()
        
	def __str__(self):
            if self.title() is not None:
		return self.title()
            return ""

	def title(self):
		return self.anchor.friendly_name
	
	def teachers(self):
		v = GetNode( 'V/Administer/Program/Class' )
		return [ x.user for x in UserBit.bits_get_users( self.anchor, v ) ]

	def preregister_student(self, user):
		prereg = UserBit()
		prereg.user = user
		prereg.qsc = self.anchor
		prereg.verb = GetNode( 'V/Preregister' )
		prereg.save()

	class Admin:
		pass
	
class TeacherBio(models.Model):
	""" A biography of an ESP teacher """
	user = models.ForeignKey(User)
	content = models.TextField()

	def __str__(self):
		return self.user.first_name + ' ' + self.user.last_name + ', a Biography'
	
	def html(self):
		return markdown(self.content)
	
	class Admin:
		pass

class RegistrationProfile(models.Model):
	""" A student registration form """
	user = models.ForeignKey(User)
	program = models.ForeignKey(Program)
	contact_student = models.ForeignKey(ContactInfo, blank=True, null=True, related_name='as_student')
	contact_guardian = models.ForeignKey(ContactInfo, blank=True, null=True, related_name='as_guardian')
	contact_emergency = models.ForeignKey(ContactInfo, blank=True, null=True, related_name='as_emergency')

	def __str__(self):
		return '<Registration for ' + str(self.user) + ' in ' + str(self.program) + '>'
	
	def preregistered_classes(self):
		v = GetNode( 'V/Preregister' )
		return UserBit.find_by_anchor_perms(Class, self.user, v, self.program.anchor.tree_decode(['Classes']))
	def registered_classes(self):
		v = GetNode( 'V/Subscribe' )
		return UserBit.find_by_anchor_perms(Class, self.user, v, self.program.anchor.tree_decode(['Classes']))

	class Admin:
		pass
