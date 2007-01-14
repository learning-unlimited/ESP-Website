from django.db import models
from django.contrib.auth.models import User, AnonymousUser
from esp.datatree.models import DataTree, PermToString, GetNode, StringToPerm
#from peak.api import security, binding
from esp.workflow.models import Controller
from datetime import datetime
from django.db.models import Q
from esp.dblog.models import error
from django.db.models.query import QuerySet
from esp.lib.EmptyQuerySet import EMPTY_QUERYSET
from django.core.cache import cache


class ESPUser(User, AnonymousUser):
    """ Create a user of the ESP Website
    This user extends the auth.User of django"""

    # this will allow a casting from User to ESPUser:
    #      foo = ESPUser(bar)   <-- foo is now an ``ESPUser''
    def __init__(self, userObj):
        self.__dict__ = userObj.__dict__

    def getVisible(self, objType):
        return UserBit.find_by_anchor_perms(objType, self, GetNode('V/Flags/Public'))

    def getEditable(self, objType):
        return UserBit.find_by_anchor_perms(objType, self, GetNode('V/Administer/Edit'))

    def getTaughtClasses(self):
        from esp.program.models import Class
        return UserBit.find_by_anchor_perms(Class, self, GetNode('V/Flags/Registration/Teacher'))

    def getEnrolledClasses(self):
        from esp.program.models import Class
        Conf = UserBit.find_by_anchor_perms(Class, self, GetNode('V/Flags/Registration/Confirmed'))
        Prel = UserBit.find_by_anchor_perms(Class, self, GetNode('V/Flags/Registration/Preliminary'))

        return (Conf | Prel).distinct()
        
    def canAdminister(self, nodeObj):
        return UserBit.UserHasPerms(self, nodeObj.anchor, GetNode('V/Administer'))

    def isTeacher(self):
        """Returns true if this user is a teacher"""
        return UserBit.UserHasPerms(self, GetNode('Q'), GetNode('V/Flags/UserRole/Teacher'),datetime.now())

    def isStudent(self):
        """Returns true if this user is a teacher"""
        return UserBit.UserHasPerms(self, GetNode('Q'), GetNode('V/Flags/UserRole/Student'),datetime.now())

    def canEdit(self, nodeObj):
        """Returns True or False if the user can edit the node object"""
        # Axiak
        return UserBit.UserHasPerms(self, nodeObj.anchor, GetNode('V/Administer/Edit'))

    def getMiniBlogEntries(self):
        """Return all miniblog posts this person has V/Subscribe bits for"""
        # Axiak 12/17
        from esp.miniblog.models import Entry
        return UserBit.find_by_anchor_perms(Entry, self, GetNode('V/Subscribe')).order_by('-timestamp')

    @staticmethod
    def isUserNameTaken(username):
        return User.objects.filter(username=username.lower()).count() > 0
   

class UserBit(models.Model):
    """ Grant a user a bit on a Q """
    user = models.ForeignKey(User, blank=True, null=True) # User to give this permission
    qsc = models.ForeignKey(DataTree, related_name='permission_related_field') # Controller to grant access to
    verb = models.ForeignKey(DataTree, related_name='subject_related_field') # Do we want to use Subjects?

    startdate = models.DateTimeField(blank=True, null=True)
    enddate = models.DateTimeField(blank=True, null=True)

    recursive = models.BooleanField(default=True)

    def __str__(self):
        curr_user = '?'
        curr_qsc = '?'
        curr_verb = '?'

        try:
            if self.user is None:
                curr_user = 'Everyone'
            else:
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

        if self.recursive:
            recurse = ""
        else:
            recurse = " (non-recursive)"
        
        if self.startdate != None and self.enddate != None:
            return 'GRANT ' + curr_user + ' ' + curr_verb + ' ON ' + curr_qsc + ' <' + str(self.startdate) + ' - ' + str(self.enddate) + '>' + recurse
        else:
            return 'GRANT ' + curr_user + ' ' + curr_verb + ' ON ' + curr_qsc + recurse

    @staticmethod
    def UserHasPerms(user, qsc, verb, now = None):
        """ Given a user, a permission, and a subject, return True if the user, or all users, has been Granted [subject] on [permission]; False otherwise """
        # aseering: This reeks of code redundancy; is there a way to combine the above and below loops into a single loop?
        # aseering 1-11-2007: Even better; single query!

        if user==None:
            user_id="None"
        else:
            user_id=str(user.id)

        if now == None:
            now = datetime.now()
            now_id = "None"
        else:
            now_id = "-".join([ str(i) for i in datetime.now().timetuple() ])

        cache_id = 'UserHasPerms:' + user_id + ',' + str(qsc.id) + ',' + str(verb.id) + ',' + now_id
        cached_val = cache.get(cache_id)
        if cached_val != None:
            return cached_val

        # Filter by user
        if user != None and user.is_authenticated():
            base_userbit = UserBit.objects.filter(Q(user__isnull=True) | Q(user=user))
        else:
            base_userbit = UserBit.objects.filter(user__isnull=True)

        # Filter by date/time range
        base_userbit = base_userbit.filter(Q(startdate__isnull=True) | Q(startdate__lte=now), Q(enddate__isnull=True) | Q(enddate__gt=now))

        # filter by qsc and verb
        recursive_userbit = base_userbit.filter(recursive=True, qsc__rangestart__lte=qsc.rangestart, qsc__rangeend__gte=qsc.rangeend, verb__rangestart__lte=verb.rangestart, verb__rangeend__gte=verb.rangeend)
        flat_userbit = base_userbit.filter(recursive=False, qsc=qsc, verb=verb)

        # If we have at least one UserBit meeting these criteria, we have perms.
        final_userbit = (recursive_userbit | flat_userbit)

        retVal = (final_userbit.count() >= 1)

        # Cache the result for up to 10sec.
        # That had better be long enough for even the most painful page renders...
        cache.set(cache_id, retVal, 10)

        return retVal
    
    # FIXME: This looks like it has been subject to extreme code rot
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
    def bits_get_users(qsc, verb, now = datetime.now(), end_of_now = None):
        """ Return all users who have been granted 'verb' on 'qsc' """
        if end_of_now == None: end_of_now = now

        #	Hopefully it's easier to understand this query now...
        Q_correct_userbit = Q(recursive = True, verb__rangestart__lte = verb.rangestart, verb__rangeend__gte = verb.rangeend)
        Q_correct_qsc = Q(qsc=qsc)
        Q_exact_match = Q(recursive = False, verb=verb, qsc=qsc)
        Q_after_start = Q(startdate__isnull = True) | Q(startdate__lte = end_of_now)
        Q_before_end = Q(enddate__isnull = True) | Q(enddate__gte = now)
		
        users = UserBit.objects.filter(Q_exact_match).filter(Q_after_start).filter(Q_before_end) | UserBit.objects.filter(Q_correct_qsc).filter(Q_correct_userbit).filter(Q_after_start).filter(Q_before_end)

        return users.distinct()
    

    @staticmethod
    def bits_get_qsc(user, verb, now = datetime.now(), end_of_now = None, qsc_root=None):
        """  Return all qsc structures to which 'user' has been granted 'verb'

        If 'qsc_root' is specified, only return qsc structures at or below the specified node """
        if end_of_now == None: end_of_now = now

        #	Hopefully it's easier to understand this query now...
        Q_correct_userbit = Q(recursive = True, verb__rangestart__lte = verb.rangestart, verb__rangeend__gte = verb.rangeend)
        Q_exact_match = Q(recursive = False, verb=verb)
        Q_correct_user = Q(user__isnull = True) | Q(user=user)

        if not user.is_authenticated():
            Q_correct_user = Q(user__isnull = True)
            
        Q_after_start = Q(startdate__isnull = True) | Q(startdate__lte = end_of_now)
        Q_before_end = Q(enddate__isnull = True) | Q(enddate__gte = now)
		
        qscs = UserBit.objects.filter(Q_exact_match).filter(Q_correct_user).filter(Q_after_start).filter(Q_before_end) | UserBit.objects.filter(Q_correct_userbit).filter(Q_correct_user).filter(Q_after_start).filter(Q_before_end)

        if qsc_root == None:
            return qscs.distinct()
        else:
            return qscs.filter(qsc__rangestart__gte=qsc_root.rangestart, qsc__rangeend__lte=qsc_root.rangeend).distinct()

    @staticmethod
    def bits_get_verb(user, qsc, now = datetime.now(), end_of_now = None):
        """ Return all verbs that 'user' has been granted on 'qsc' """
        if end_of_now == None: end_of_now = now

        #	Hopefully it's easier to understand this query now...
        Q_correct_userbit = Q(recursive = True, qsc__rangestart__lte = qsc.rangestart, qsc__rangeend__gte = qsc.rangeend)
        Q_exact_match = Q(recursive = False, qsc=qsc)
        Q_correct_user = Q(user__isnull = True) | Q(user=user)

        if not user.is_authenticated():
            Q_correct_user = Q(user__isnull = True)
            
        Q_after_start = Q(startdate__isnull = True) | Q(startdate__lte = end_of_now)
        Q_before_end = Q(enddate__isnull = True) | Q(enddate__gte = now)
		
        verbs = UserBit.objects.filter(Q_exact_match).filter(Q_correct_user).filter(Q_after_start).filter(Q_before_end) | UserBit.objects.filter(Q_correct_userbit).filter(Q_correct_user).filter(Q_after_start).filter(Q_before_end)

        return verbs.distinct()
        
        #return UserBit.objects.filter(Q(recursive=True, qsc__rangestart__gte=qsc.rangestart, qsc__rangeend__lte=qsc.rangeend) | Q(qsc__pk=qsc.id)).filter(Q(user__isnull=True)|Q(user__pk=user.id)).filter(Q(startdate__isnul=True) | Q(startdate__lte=end_of_now), Q(enddate__isnull=True) | Q(enddate__gte=now))

    @staticmethod
    def has_bits(queryset):
        """ Returns False if there are no elements in queryset """
        return ( queryset.count() > 0 )

    @staticmethod
    def find_by_anchor_perms(module,user,verb,qsc=None):
    	""" Fetch a list of relevant items for a given user and verb in a module that has an anchor foreign key into the DataTree """
    	#q_list = [ x.qsc for x in UserBit.bits_get_qsc( user, verb ) ]
        q_list = UserBit.bits_get_qsc( user, verb )
    	# Extract entries associated with a particular branch

        res = None

        for bit in q_list:
            q = bit.qsc

            if bit.recursive:
                query = module.objects.filter(anchor__rangestart__gte = q.rangestart, anchor__rangestart__lt = q.rangeend)
            else:
                query = module.objects.filter(anchor=q)
                
            if qsc is not None:
                query = query.filter(anchor__rangestart__gte=qsc.rangestart, anchor__rangeend__lte=qsc.rangeend)

            if res == None:
                res = query
            else:
                res = res | query

        if res != None:
            res = res.distinct()

        if res == None:
            return EMPTY_QUERYSET.distinct()

	# Operation Complete!
	return res

    class Admin:
        pass

    
class StudentInfo(models.Model):
    """ ESP Student-specific contact information """
    user = models.ForeignKey(User, blank=True, null=True)
    graduation_year = models.PositiveIntegerField(blank=True, null=True)
    school = models.CharField(maxlength=256,blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    
    def updateForm(self, form_dict):
        form_dict['graduation_year'] = self.graduation_year
        form_dict['school']          = self.school
        form_dict['dob']             = self.dob
        return form_dict        

    @staticmethod
    def addOrUpdate(curUser, regProfile, new_data):
        """ adds or updates a StudentInfo record """
        if regProfile.student_info is None:
            studentInfo = StudentInfo()
            studentInfo.user = curUser
        else:
            studentInfo = regProfile.student_info
        
        studentInfo.graduation_year = new_data['graduation_year']
        studentInfo.school          = new_data['school']
        studentInfo.dob             = new_data['dob']
        studentInfo.save()
        return studentInfo
    
    def __str__(self):
        username = ""
        if self.user != None:
            username = self.user.username
        return 'ESP Student Info (%s)' % username
            
    class Admin:
        pass

class TeacherInfo(models.Model):
    """ ESP Teacher-specific contact information """
    user = models.ForeignKey(User, blank=True, null=True)
    graduation_year = models.PositiveIntegerField(blank=True, null=True)
    college = models.CharField(maxlength=128,blank=True, null=True)
    major = models.CharField(maxlength=32,blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    
    def updateForm(self, form_dict):
        form_dict['graduation_year'] = self.graduation_year
        form_dict['school']          = self.college
        form_dict['major']           = self.major
        form_dict['dob']             = self.dob
        return form_dict
    
    @staticmethod
    def addOrUpdate(curUser, regProfile, new_data):
        """ adds or updates a TeacherInfo record """
        if regProfile.teacher_info is None:
            teacherInfo = TeacherInfo()
            teacherInfo.user = curUser
        else:
            teacherInfo = regProfile.teacher_info
        
        teacherInfo.graduation_year = new_data['graduation_year']
        teacherInfo.college         = new_data['school']
        teacherInfo.major           = new_data['major']
        teacherInfo.dob           = new_data['dob']        
        teacherInfo.save()
        return teacherInfo
                    
    def __str__(self):
        username = ""
        if self.user != None:
            username = self.user.username
        return 'ESP Teacher Info (%s)' % username

    class Admin:
        pass
    
class GuardianInfo(models.Model):
    """ ES Guardian-specific contact information """
    user = models.ForeignKey(User, blank=True, null=True)
    year_finished = models.PositiveIntegerField(blank=True, null=True)
    num_kids = models.PositiveIntegerField(blank=True, null=True)

    def updateForm(self, form_dict):
        form_dict['year_finished'] = self.year_finished
        form_dict['num_kids']      = self.num_kids
        return form_dict
    
    @staticmethod
    def addOrUpdate(curUser, regProfile, new_data):
        """ adds or updates a GuardianInfo record """
        if regProfile.guardian_info is None:
            guardianInfo = GuardianInfo()
            guardianInfo.user = curUser
        else:
            guardianInfo = regProfile.guardian_info
        
        guardianInfo.year_finished = new_data['year_finished']
        guardianInfo.num_kids      = new_data['num_kids']
        guardianInfo.save()
        return guardianInfo
    
    def __str__(self):
        username = ""
        if self.user != None:
            username = self.user.username
        return 'ESP Guardian Info (%s)' % username
    
    class Admin:
        pass

class EducatorInfo(models.Model):
    """ ESP Educator-specific contact information """
    user = models.ForeignKey(User, blank=True, null=True)
    subject_taught = models.CharField(maxlength=64,blank=True, null=True)
    grades_taught = models.CharField(maxlength=16,blank=True, null=True)
    school = models.CharField(maxlength=128,blank=True, null=True)
    position = models.CharField(maxlength=64,blank=True, null=True)
    
    def updateForm(self, form_dict):
        form_dict['subject_taught'] = self.subject_taught
        form_dict['grades_taught']  = self.grades_taught
        form_dict['school']         = self.school
        form_dict['position']       = self.position        
        return form_dict
    
    @staticmethod
    def addOrUpdate(curUser, regProfile, new_data):
        """ adds or updates a EducatorInfo record """
        if regProfile.educator_info is None:
            educatorInfo = EducatorInfo()
            educatorInfo.user = curUser
        else:
            educatorInfo = regProfile.educator_info
        
        educatorInfo.subject_taught = new_data['subject_taught']
        educatorInfo.grades_taught  = new_data['grades_taught']
        educatorInfo.position       = new_data['position']      
        educatorInfo.school         = new_data['school']
        educatorInfo.save()
        return educatorInfo
        
    def __str__(self):
        username = ""
        if self.user != None:
            username = self.user.username
        return 'ESP Educator Info (%s)' % username

    
    class Admin:
        pass
    
class ContactInfo(models.Model):
	""" ESP-specific contact information for (possibly) a specific user """
	user = models.ForeignKey(User, blank=True, null=True)
	first_name = models.CharField(maxlength=64)
	last_name = models.CharField(maxlength=64)        
	e_mail = models.EmailField(blank=True, null=True)
	phone_day = models.PhoneNumberField(blank=True, null=True)
	phone_cell = models.PhoneNumberField(blank=True, null=True)
	phone_even = models.PhoneNumberField(blank=True, null=True)
	address_street = models.CharField(maxlength=100,blank=True, null=True)
	address_city = models.CharField(maxlength=50,blank=True, null=True)
	address_state = models.USStateField(blank=True, null=True)
	address_zip = models.CharField(maxlength=5,blank=True, null=True)

        @staticmethod
        def addOrUpdate(regProfile, new_data, contactInfo, prefix='', curUser=None):
            """ adds or updates a ContactInfo record """
            if contactInfo is None:
                contactInfo = ContactInfo()
            for i in contactInfo.__dict__.keys():
                if i != 'user_id' and i != 'id' and new_data.has_key(prefix+i):
                    contactInfo.__dict__[i] = new_data[prefix+i]
            if curUser is not None:
                contactInfo.user = curUser
            contactInfo.save()
            return contactInfo

        def updateForm(self, form_data, prepend=''):
            newkey = self.__dict__
            for key, val in newkey.items():
                if val and key != 'id':
                    form_data[prepend+key] = str(val)

            return form_data
        
	def __str__(self):
            username = ""
            last_name, first_name = '', ''
            if self.user != None:
                username = self.user.username
            if self.first_name is not None:
                first_name = self.first_name
            if self.last_name is not None:
                last_name = self.last_name
            return first_name + ' ' + last_name + ' (' + username + ')'
	
	class Admin:
		pass

def GetNodeOrNoBits(nodename, user = AnonymousUser(), verb = None):
    """ Get the specified node.  Create it only if the specified user has create bits on it """
    if user == None or not user.is_authenticated():
        user_id = "None"
    else:
        user_id = user.username

    if verb == None:
        verb_id = "None"
    else:
        verb_id = str(verb.id)

    cache_id = 'datatree:' + user_id + ',' + str(verb_id) + ',' + nodename

    cached_val = cache.get(cache_id)
    if cached_val != None:
        return cached_val

    cached_val = cache.get

    nodes = DataTree.objects.filter(name='ROOT', parent__isnull=True)
    node = None
    if nodes.count() < 1L:
        error("Trying to create a new root node here.  Dying...")
        assert False, "Trying to create a new root node here.  Dying..."
        node = DataTree()
        node.name = 'ROOT'
        node.parent = None
        node.save()
    elif nodes.count() == 1L:
        node = nodes[0]
    else:
        raise DataTree.NoRootNodeException(nodes.count())
    
    perm = StringToPerm(nodename)
    if nodename == '':
        perm = []

    try:
        retVal = node.tree_decode(perm)

        if retVal.id == -1:
            pass

        cache.set(cache_id, retVal)
        return retVal
    except DataTree.NoSuchNodeException, e:
        if verb == None:
            verb = GetNode("V/Administer/Program/Class")

        if UserBit.UserHasPerms(user, e.anchor, verb):
            retVal = e.anchor.tree_create(e.remainder)

            if retVal.id == -1:
                pass

            cache.set(cache_id, retVal)
            return retVal
        else:
            raise

