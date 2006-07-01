from django.db import models
from django.contrib.auth.models import User, AnonymousUser
from esp.watchlists.models import Datatree, PermToString
from peak.api import security, binding
from esp.workflow.models import Controller
from datetime import datetime

# Create your models here.

class ESPUser(models.Model):
    """ Create a user of the ESP Website """
    user = models.OneToOneField(User) # Django user that we're connected to
#    bits = models.ManyToMany(Datatree)

class UserBit(models.Model):
    """ Grant a user bits to a controller """
    user = models.ForeignKey(ESPUser) # User to give this permission
    qsc = models.ForeignKey(Datatree, related_name='permission_related_field') # Controller to grant access to
    verb = models.ForeignKey(Datatree, related_name='subject_related_field') # Do we want to use Subjects?

    startdate = models.DateTimeField(default=datetime.min)
    enddate = models.DateTimeField(default=datetime.max)

    def __str__(self):
        curr_user = '?'
        curr_qsc = '?'
        curr_verb = '?'

        try:
            curr_user = str(self.user.user)
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

    def espUserHasPerms(self, qsc, verb, now = datetime.now()):
        """ Given a user, a permission, and a subject, return True if the user, or all users, has been Granted [subject] on [permission]; False otherwise """
        user = self
        
        if user != None:
            for bit in user.userbit_all().filter(startdate_lt=now, enddate_gt=now):
                if bit.qsc.is_descendant(qsc) & bit.verb.is_antecedent(verb):
                    return True

            # This reeks of code redundancy; is there a way to combine the above and below loops into a single loop?
            for bit in UserBit.objects.filter(user_pk=AnonymousUser().id, startdate_lt=now, enddate_gt=now):
                if bit.qsc.is_descendant(qsc) & bit.verb.is_antecedent(verb):
                    return True

        # security.Denial() evaluates to False as necessary; it also makes peak happy, though we're not using peak any more
        return security.Denial("User " + str(user) + " doesn't have the permission " + str(perm))

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
        return UserBit.objects.filter(qsc__rangestart__gte=qsc.rangestart, qsc__rangeend__lte=qsc.rangeend, verb__rangestart__lte=verb.rangestart, verb__rangeend__gte=verb.rangeend).exclude(startdate__gt=now).exclude(enddate__lt=now)

    @staticmethod
    def bits_get_qsc(user, verb, now = datetime.now()):
        """  Return all qsc structures to which 'user' has been granted 'verb' """
        now = datetime.now()
        return UserBit.objects.filter(verb__rangestart__lte=verb.rangestart, verb__rangeend__gte=verb.rangeend, user_pk=user.id).exclude(startdate__gt=now).exclude(enddate__lt=now)

    @staticmethod
    def bits_get_verb(user, qsc, now = datetime.now()):
        """ Return all verbs that 'user' has been granted on 'qsc' """        
        return UserBit.objects.filter(qsc__rangestart__gte=qsc.rangestart, qsc__rangeend__lte=qsc.rangeend, user_pk=user.id).exclude(startdate__gt=now).exclude(enddate__lt=now)


    @staticmethod
    def has_bits(queryset):
        """ Returns False if there are no elements in queryset """
        return ( queryset.count() > 0 )
