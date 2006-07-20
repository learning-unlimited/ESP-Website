from django.db import models
from django.contrib.auth.models import User, AnonymousUser
from esp.datatree.models import DataTree, PermToString
#from peak.api import security, binding
from esp.workflow.models import Controller
from datetime import datetime
from django.db.models import Q

# Create your models here.

#class ESPUser(models.Model):
#    """ Create a user of the ESP Website """
#    user = models.OneToOneField(User) # Django user that we're connected to
#
#    class Admin:
#        pass

class UserBit(models.Model):
    """ Grant a user bits to a controller """
    user = models.ForeignKey(User, blank=True, null=True) # User to give this permission
    qsc = models.ForeignKey(DataTree, related_name='permission_related_field') # Controller to grant access to
    verb = models.ForeignKey(DataTree, related_name='subject_related_field') # Do we want to use Subjects?

    startdate = models.DateTimeField(blank=True, null=True)
    enddate = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        curr_user = '?'
        curr_qsc = '?'
        curr_verb = '?'

        try:
            curr_user = str(self.user)
        except Exception:
            pass

        try:
            curr_qsc = PermToString(self.qsc.tree_encode())
        except Exception:
            pass

        try:
            curr_verb = PermToString(self.verb.tree_encode())
        except Exception:
            pass
        
        return 'GRANT ' + curr_user + ' ' + curr_verb + ' ON ' + curr_qsc

    @staticmethod
    def UserHasPerms(user, qsc, verb, now = datetime.now()):
        """ Given a user, a permission, and a subject, return True if the user, or all users, has been Granted [subject] on [permission]; False otherwise """
	test = []
        if user != None:
            for bit in user.userbit_set.all().filter(Q(startdate__isnull=True) | Q(startdate__lte=now), Q(enddate__isnull=True) | Q(enddate__gt=now)):
                test.append(bit)
                if bit.qsc.is_descendant(qsc) and bit.verb.is_antecedent(verb):
                    return True

            # This reeks of code redundancy; is there a way to combine the above and below loops into a single loop?
        for bit in UserBit.objects.filter(user__isnull=True).filter(Q(startdate__isnull=True) | Q(startdate__lte=now), Q(enddate__isnull=True) | Q(enddate__gt=now)):
            test.append(bit)
            if bit.qsc.is_descendant(qsc) and bit.verb.is_antecedent(verb):
                return True

        # security.Denial() evaluates to False as necessary; it also makes peak happy, though we're not using peak any more
        #return security.Denial("User " + str(user) + " doesn't have the permission " + str(perm))
	assert False
        return False
    
    @staticmethod
    def enforce_bits(controller_class, user):
        def call(proc, *args):
            """ Accepts a 'run' function, its associated Controller class (is there a way to getthat information automatically, from the function?), and a user; returns a function that runs the 'run' function and returns 'true' if the user can access this Controller class, and returns 'false' otherwise. """
            proc(args)
            return True

        if UserBit.objects.filter(permission__controller=controller_class.__name__).filter(user_pk=user.id).count() != 0:
            return decorator(call)
        else:
            return lambda : False

    @staticmethod
    def bits_get_users(qsc, verb, now = datetime.now()):
        """ Return all users who have been granted 'verb' on 'qsc' """
        now = datetime.now()
        return UserBit.objects.filter(qsc__rangestart__lte=qsc.rangestart, qsc__rangeend__gte=qsc.rangeend, verb__rangestart__gte=verb.rangestart, verb__rangeend__lte=verb.rangeend).filter(Q(startdate__isnull=True) | Q(startdate__gt=now), Q(enddate__isnull=True) | Q(enddate__lt=now))

    @staticmethod
    def bits_get_qsc(user, verb, now = datetime.now()):
        """  Return all qsc structures to which 'user' has been granted 'verb' """
        now = datetime.now()
        return UserBit.objects.filter(verb__rangestart__lte=verb.rangestart, verb__rangeend__gte=verb.rangeend).filter(Q(user__isnull=True)|Q(user__pk=user.id)).filter(Q(startdate__isnull=True) | Q(startdate__gt=now), Q(enddate__isnull=True) | Q(enddate__lt=now))

    @staticmethod
    def bits_get_verb(user, qsc, now = datetime.now()):
        """ Return all verbs that 'user' has been granted on 'qsc' """        
        return UserBit.objects.filter(qsc__rangestart__gte=qsc.rangestart, qsc__rangeend__lte=qsc.rangeend).filter(Q(user__isnull=True)|Q(user__pk=user.id)).filter(Q(startdate__isnul=True) | Q(startdate__gt=now), Q(enddate__isnull=True) | Q(enddate__lt=now))

    @staticmethod
    def has_bits(queryset):
        """ Returns False if there are no elements in queryset """
        return ( queryset.count() > 0 )

    @staticmethod
    def find_by_anchor_perms(module,user,verb,qsc=None):
    	""" Fetch a list of relevant items for a given user and verb in a module that has an anchor foreign key into the DataTree """
    	q_list = [ x.qsc for x in UserBit.bits_get_qsc( user, verb ) ]

    	# FIXME: This code should be compressed into a single DB query
    	# ...using the extra() QuerySet method.

    	# Extract entries associated with a particular branch
    	res = []
    	for q in q_list:
    		for entry in module.objects.filter(anchor__rangestart__gte = q.rangestart, anchor__rangestart__lt = q.rangeend):
			if qsc is not None:
				if entry.anchor.rangestart < qsc.rangestart or entry.anchor.rangeend >= qsc.rangeend:
					continue
     			res.append( entry )
	
	# Operation Complete!
	return res

    class Admin:
        pass
    
class ContactInfo(models.Model):
	""" ESP-specific contact information for (possibly) a specific user """
	user = models.ForeignKey(User, blank=True, null=True)
	full_name = models.CharField(maxlength=256)
	dob = models.DateField(blank=True, null=True)
	graduation_year = models.PositiveIntegerField(blank=True, null=True)
	e_mail = models.EmailField(blank=True, null=True)
	phone_day = models.PhoneNumberField(blank=True, null=True)
	phone_cell = models.PhoneNumberField(blank=True, null=True)
	phone_even = models.PhoneNumberField(blank=True, null=True)
	address_street = models.CharField(maxlength=100)
	address_city = models.CharField(maxlength=50)
	address_state = models.USStateField()
	address_zip = models.CharField(maxlength=5)

	def __str__(self):
            username = ""
            if self.user != None:
                username = self.user.username
                
            return self.full_name + ' (' + username + ')'
	
	class Admin:
		pass
