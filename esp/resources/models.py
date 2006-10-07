from django.db import models
from esp.datatree.models import DataTree
from datetime import datetime

# Create your models here.

class ResourceType(models.Model):
    """ A type of resource, ie. a projector, a classroom, a box of chalk """
    description = models.TextField() # In as few words as possible, preferably one or two, what is this resource?
    consumable = models.BooleanField() # Does this resource get used up?

    class Admin:
        pass

class Resource(models.Model):
    """ An instance of a ResourceType.  If the office has four projectors, it'll have a 'Projector' ResourceType, and four Resource instances with type 'Projector' """
    resource_type = models.ForeignKey(ResourceType)
    amount_left = models.FloatField(max_digits=8, decimal_places=3, blank=True, null=True) # if resource_type.consumable, how much of this stuff do we have left?  If not resource_type.consumable, should = None
    notes = models.TextField() # Any notes about this item; ie. "Missing power cable", etc.

    identifier = models.CharField(maxlength=128, blank=True) # A serial number, or equivalent, to identify this item uniquely

    # anchor = models.ForeignKey(DataTree) # We're not anchoring to the tree directly; we're using a userbit-esque system.

    class Admin:
        pass

# aseering 8/25/2006: This is really the wrong way to do this; it's basically a straight Copy'n'Paste from the UserBits table.
# The right way might be a Universal ForeignKey in that table; I'm not sure.
# This is quick, dirty, and works, though.
class ResourceBit(models.Model):
    """ Grant a resource a bit on a Q """
    resource = models.ForeignKey(Resource) # Resource to give to this permission
    qsc = models.ForeignKey(DataTree, related_name='qsc') # QSC to grant access to
    verb = models.ForeignKey(DataTree, related_name='verb') # Bit to grant

    startdate = models.DateTimeField(blank=True, null=True)
    enddate = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        curr_resource = '?'
        curr_qsc = '?'
        curr_verb = '?'
        
        try:
            curr_resource = str(self.resource)
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
        
        if self.startdate != None and self.enddate != None:
            return 'GRANT ' + curr_resource + ' ' + curr_verb + ' ON ' + curr_qsc + ' <' + str(self.startdate) + ' - ' + str(self.enddate) + '>'
        else:
            return 'GRANT ' + curr_resource + ' ' + curr_verb + ' ON ' + curr_qsc


    @staticmethod
    def ResourceHasPerms(resource, qsc, verb, now = datetime.now()):
        """ Given a resource, a permission, and a subject, return True if the resource, or all resource, has been Granted [subject] on [permission]; False otherwise """
        test = []
        if resource != None:
            for bit in resource.resourcebit_set.all().filter(Q(startdate__isnull=True) | Q(startdate__lte=now), Q(enddate__isnull=True) | Q(enddate__gt=now)):
                test.append(bit)
                if bit.qsc.is_descendant(qsc) and bit.verb.is_antecedent(verb):
                    return True
                
        # This reeks of code redundancy; is there a way to combine the above and below loops into a single loop?
        for bit in ResourceBit.objects.filter(resource__isnull=True).filter(Q(startdate__isnull=True) | Q(startdate__lte=now), Q(enddate__isnull=True) | Q(enddate__gt=now)):
            test.append(bit)
            if bit.qsc.is_descendant(qsc) and bit.verb.is_antecedent(verb):
                return True
                    
        return False

    @staticmethod
    def enforce_bits(controller_class, resource):
        def call(proc, *args):
            """ Accepts a 'run' function, its associated Controller class (is there a way to getthat information automatically, from the function?), and a resource; returns a function that runs the 'run' function and returns 'true' if the resource can access this Controller class, and returns 'false' otherwise. """
            proc(args)
            return True
        
        if ResourceBit.objects.filter(permission__controller=controller_class.__name__).filter(resource_pk=resource.id).count() != 0:
            return decorator(call)
        else:
            return lambda : False

    @staticmethod
    def bits_get_resources(qsc, verb, now = datetime.now(), end_of_now = None):
        """ Return all resources who have been granted 'verb' on 'qsc' """
        if end_of_now == None: end_of_now = now
        
        return ResourceBit.objects.filter(qsc__rangestart__lte=qsc.rangestart, qsc__rangeend__gte=qsc.rangeend, verb__rangestart__gte=verb.rangestart, verb__rangeend__lte=verb.rangeend).filter(Q(startdate__isnull=True) | Q(startdate__lte=end_of_now), Q(enddate__isnull=True) | Q(enddate__gte=now))

    @staticmethod
    def bits_get_qsc(resource, verb, now = datetime.now(), end_of_now = None, qsc_root=None):
        """  Return all qsc structures to which 'resource' has been granted 'verb'
        
        If 'qsc_root' is specified, only return qsc structures at or below the specified node """
        if end_of_now == None: end_of_now = now

        qscs = ResourceBit.objects.filter(verb__rangestart__lte=verb.rangestart, verb__rangeend__gte=verb.rangeend).filter(Q(resource__isnull=True)|Q(resource__pk=resource.id)).filter(Q(startdate__isnull=True) | Q(startdate__lte=end_of_now), Q(enddate__isnull=True) | Q(enddate__gte=now))

        if qsc_root == None:
            return qscs
        else:
            return qscs.filter(qsc__rangestart__gte=qsc_root.rangestart, qsc__rangeend__lte=qsc_root.rangeend)
        
    @staticmethod
    def bits_get_verb(resource, qsc, now = datetime.now(), end_of_now = None):
        """ Return all verbs that 'resource' has been granted on 'qsc' """
        if end_of_now == None: end_of_now = now
        
        return ResourceBit.objects.filter(qsc__rangestart__gte=qsc.rangestart, qsc__rangeend__lte=qsc.rangeend).filter(Q(resource__isnull=True)|Q(resource__pk=resource.id)).filter(Q(startdate__isnul=True) | Q(startdate__lte=end_of_now), Q(enddate__isnull=True) | Q(enddate__gte=now))

    @staticmethod
    def has_bits(queryset):
        """ Returns False if there are no elements in queryset """
        return ( queryset.count() > 0 )

    @staticmethod
    def find_by_anchor_perms(module,resource,verb,qsc=None):
        """ Fetch a list of relevant items for a given resource and verb in a module that has an anchor foreign key into the DataTree """
        q_list = [ x.qsc for x in ResourceBit.bits_get_qsc( resource, verb ) ]
        
        # FIXME: This code should be compressed into a single DB query
        # ...using the extra() QuerySet method.
        
        # Extract entries associated with a particular branch
        res = []
        for q in q_list:
            for entry in module.objects.filter(anchor__rangestart__gte = q.rangestart, anchor__rangestart__lt = q.rangeend):
                if qsc is not None:
                    if entry.anchor.rangestart < qsc.rangestart or entry.anchor.rangeend > qsc.rangeend:
                        continue
                    res.append( entry )
                    
                    # Operation Complete!
                    return res
                
    class Admin:
        pass
                                                                                                                                                            
