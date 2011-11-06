path_to_esp = '/esp/esp/'

import sys
sys.path += [path_to_esp, path_to_esp + 'esp/']

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

import random

from esp.cal.models import Event
from esp.users.models import User, ESPUser
from esp.program.models import Program, ClassSection, StudentRegistration, RegistrationType

################################
# Global Settings and Thingies #
################################

# Priority and Interested registration types for use with assignments.
priority_type = 'Priority/1'
interested_type = 'Interested'
enrolled_type = 'Enrolled'

# Numerical parameters for assigning students a score for getting into classes.
onestar = 1
twostar = 1.2
twostarstar = 1.1

# Range for random number generation.  A random number will be generated
# in this range, and multiplied by the value, for some randomness.
# Not using this, as I don't think it's fair enough.  We're just
# multiplying by a float in (0, 1).
rangemin = 0
rangesize = 1

# The program used for these scripts.
# Spark 2011 is the most recent class as of this commit
program = Program.objects.order_by('-id')[0]
print "Initialized program to", program

# Lunch hours, for checking whether a student has lunch free.
#satlunch = tuple([int(x.id) for x in Event.objects.filter(id__in=[522,518])]) # for Spark 2011, lunch is 12-1, 1-2 on Saturday, March 18
satlunch = (552, 553)
# no Sunday lunch for Spark
# commented out all lines in the program that included sunlunch; for Splash, these should be uncommented
sunlunch = tuple([int(x.id) for x in Event.objects.filter(id__in=[566,567])])

# The wiggle room factor for the class capacity, to leave a space for
# those classes that didn't fill up from priority.  Set to 10% for now.
# This variable is the multiplicative factor.
# Seems we're not currently using this right now.
wiggle = 0.9

def class_cap(cls):
    """
    Determine the class capacity of a class as calculated by whatever
    it is we're using to calculate it for these classes.
    We're just using the class's full capacity right now, and the
    capacity is calculated in the _get_capacity function, so all is well.
    cls -- the class section in question.
    """
    return cls.capacity

def capacity_star(cls):
    """ 
    For now, we're not using this, but if we ever want to use a capacity
    that's less than the full capacity we can use this or something.
    """
    return class_cap(cls)

####################
# Helper Functions #
####################

def lunch_free(user, lunchtimes):
    secs = ESPUser(user).getEnrolledSectionsFromProgram(program)
    for sec in secs:
        mt = sec.get_meeting_times().values_list('pk',flat=True).distinct() # lunch is an id, but get_meeting_times() is a QuerySet, so we need to search through the list of its ids
        for lunch in lunchtimes: # lunchtimes is a tuple of id's
            if lunch in mt: 
                return False
    return True
    #return not bool(ESPUser(user).getEnrolledSectionsFromProgram(program).filter(meeting_times__in=lunchtimes))

# TODO(rye): Add a mechanism for lunch, with some helper functions to ensure lunch.
def try_add(user, cls):
    """
    Try to add this student to the class.  First checks whether the student
    can add the class given their current schedule and grade level,
    then assigns them to the class.

    Returns True if assignment was successful, False otherwise.
    """
    # First, check if this class runs over lunch, and if so, make sure
    # the student actually has lunch free.
    
    if not hasattr(cls, "_satlunch"):
        cls._satlunch = bool(cls.meeting_times.filter(id__in=satlunch))
    if cls._satlunch:
        if not lunch_free(user, satlunch):
            return False

    if not hasattr(cls, "_sunlunch"):
        cls._sunlunch = bool(cls.meeting_times.filter(id__in=sunlunch))
    if cls._sunlunch:
        if not lunch_free(user, sunlunch):
            return False

    # Now we've worked out any potential lunch conflicts.
    # Check if this user can actually add this section (and has no conflicts).
    error = cls.cannotAdd(user)
    if not error:
        # If there are no conflicts, check the parent class for permissions.
        error = cls.parent_class.cannotAdd(user)

    # If there's still no errors, proceed with registering the student.
    if not error:
        success = cls.preregister_student(user, prereg_verb='Enrolled')
        return success
    else:
        return False

def priority_lottery_val(user):
    """
    Calculate the probability of this student getting to the front of the
    list for getting assigned into a priority class.  Depends only
    on how many classes they've gotten in the past (more likely if fewer).

    Assume here that the only classes they've gotten into so far 
    are priority classes.  This is true given when this will be used,
    but makes it not a general function.
    """
    priority_ids = StudentRegistration.valid_objects().filter(user=user, section__parent_class__parent_program=program, relationship__name=priority_type).values_list('section', flat=True).distinct()
    reged_classes_count = StudentRegistration.valid_objects().filter(user=user, section__id__in=priority_ids, relationship__name=enrolled_type).values_list('section', flat=True).distinct().count()

    # Randomly generate a number in the range specified above.
    retval = random.random()

    if reged_classes_count > 0:
        retval *= onestar / (reged_classes_count * twostar)
    else: 
        retval *= onestar

    return retval

def interested_lottery_val(user):
    """ 
    Calculate the probability value for this user in the lottery.
    Based on how many of their priority classes the user has already gotten
    into, and how many of their interested classes the user got into.
    """

    interested_ids = StudentRegistration.valid_objects().filter(user=user, section__parent_class__parent_program=program, relationship__name=interested_type).values_list('section', flat=True).distinct()
    interested_count = StudentRegistration.valid_objects().filter(user=user, section__id__in=interested_ids, relationship__name=enrolled_type).values_list('section', flat=True).distinct().count()

    # The randomizing factor already exists in the returned value of this
    # function, so what we do here is just multiply it by more factors.
    retval = priority_lottery_val(user)

    if interested_count > 0:
        retval *= 1 / (interested_count * twostarstar)

    return retval

# Getter functions for the user, priority_value thingy
def bundle_priority(user):
    return (user, priority_lottery_val(user))

def bundle_interested(user):
    return (user, interested_lottery_val(user))

def get_user(bundle):
    return bundle[0]

def get_val(bundle):
    return bundle[1]


# Function to find all issues with currently existing registrations.
def print_issues():
    # Find students with conflicting classes.
    print "ERROR SWEEP: Looking for students with conflicting classes or multiple classes over lunch..."

    check_conflicting_classes(False)

    for student in program.students()['enrolled']:
        lunch_count = 0
        secs = ESPUser(student).getEnrolledSectionsFromProgram(program)
        for sec in secs:
            if satlunch in sec.get_meeting_times():
                lunch_count += 1
                if lunch_count > 1:
                    print ESPUser(student).name() + " (" + student.username + "), Saturday lunch conflict"                    
                    break

            if sunlunch in sec.get_meeting_times():
                lunch_count += 1
                if lunch_count > 1:
                    print ESPUser(student).name() + " (" + student.username + "), Sunday lunch conflict"                    
                    break

def check_conflicting_classes(remove):
    for student in program.students()['enrolled']:
        secs = ESPUser(student).getEnrolledSectionsFromProgram(program)
        my_tsdict = {}
        for sec in secs:
            for mt in sec.meeting_times.all():
                if int(mt.id) in my_tsdict and not my_tsdict[mt.id] == None and not my_tsdict[mt.id] == sec:
                    otherSec = my_tsdict[mt.id]
                    problem_count = problem_count + 1
                    print ESPUser(student).name() + " (" + student.username + "), conflict: " + sec.emailcode() + ", " + my_tsdict[mt.id].emailcode()
                    if remove:
                        choose_class_and_remove_student(sec, otherSec, my_tsdict, student)
                else:
                    my_tsdict[int(mt.id)] = sec

#requires otherSec be the section currently in my_tsdict for the conflicting timeslot
def choose_class_and_remove_student(sec, otherSec, my_tsdict, student):
    #to choose which section to remove, we first check whether either was the student's priority class, if not
    # we remove the students from the class with less space
    if StudentRegistration.objects.filter(section=sec, user=student, relationship__name=priority_type).count() > 0:
        removeSection = otherSec
    elif StudentRegistration.objects.filter(section=otherSec, user=student, relationship__name=priority_type).count() > 0:
        removeSection = sec
    elif sec._get_capacity() - sec.num_students() < otherSec._get_capacity() - otherSec.num_students():
        removeSection = sec
    else:
        removeSection = otherSec
    removeSection.unpreregister_student(student, enrolled_type)
    print "removed " + student.username + " from section " + removeSection.emailcode()
    if removeSection == otherSec:
        for timeslot in otherSec.get_meeting_times():
            my_tsdict[timeslot.id] = None
        for timeslot in sec.get_meeting_times():
            if timeslot.id in my_tsdict: 
                if my_tsdict[timeslot.id] == None:
                    my_tsdict[timeslot.id] = sec
                else:
                    choose_class_and_remove_student(sec, my_tsdict[timeslot.id], my_tsdict, student)
            else:
                my_tsdict[timeslot.id] = sec
            

def remove_students_in_conflicting_classes():
    check_conflicting_classes(True)

def check_sanity():
    for stu in program.students()['confirmed']:
        print stu
        d = {}
        for t in program.getTimeSlots():
            d[t] = []
        for sr in StudentRegistration.objects.filter(section__parent_class__parent_program=74, relationship__name='Enrolled', user__id=stu.id):
            for s in sr.section.get_meeting_times():
                d[s].append(sr)
        for t in d:
            if len(d[t]) == 0:
                for inter in StudentRegistration.objects.filter(section__parent_class__parent_program=74, relationship__name='Priority/1', user__id=stu.id):
                    if not inter.section.isFull():
                        if t in inter.section.get_meeting_times():
                            if len(inter.section.get_meeting_times()) == 1:
                                print t
                                print inter.section
                    
            #print "no class"
            #figure out whether there are open classes the student was interested in 

################################
# Lottery Assignment Functions #
################################

def assign_priorities():
    """
    Assign people to their priority classes.  At the end of this function
    every student will be assigned to the classes of their priorities that
    they get into.

    Phase one:
    Loop through all class sections in this program, and for each of
    these if the number of priority flags is less than the class
    capacity, enroll everybody in the class (who can be in the class).

    Phase two:
    Go through all the class sections that we didn't manage to assign
    folks to in phase one (because there were too many people who
    marked it priority), and do a preference-based lottery for the
    people who have marked this class.    
    """
    # Randomize the order in which we go through the priority classes, because
    # the algorithm doesn't specify, and we don't want to leave them in
    # database order.
    all_secs = list(program.sections().filter(status__gt=0))
    random.shuffle(all_secs)

    # These will be lists of tuples: (sec, priority-flags)
    phase1_secs = []
    phase2_secs = []

    # Division of sections into phase 1 and phase 2 sections
    for sec in all_secs:
        # First get how many students marked this as their first choice;
        # if it's greater than the class capacity, then don't deal with
        # this now.
        # Because there are duplicate registrations for each, just get the
        # distinct users who marked this class as priority.
        priority_regs = ESPUser.objects.filter(id__in=StudentRegistration.valid_objects().filter(section=sec, relationship__name=priority_type).values_list('user', flat=True)).distinct()
        if (priority_regs.count() > class_cap(sec)):
            phase2_secs.append((sec, priority_regs))
        else: 
            phase1_secs.append((sec, priority_regs))

    # Handle the phase 1 sections
    for sec, priority in phase1_secs:
        print "== Phase 1: Adding priority students to " + sec.emailcode() + ": " + sec.title() + " =="

        # Loop through all classes where priority flags is less than capacity.
        # Try to register each student for the class; we don't care if
        # it fails, because no one's competing for the spots.
        for thisuser in priority:
            success = try_add(thisuser, sec)
            if success:
                print thisuser.name() + " (" + thisuser.username + ")"

    # Handle the phase 2 sections
    for sec, priority in phase2_secs:
        print "== Phase 2: Adding priority students to " + sec.emailcode() + ": " + sec.title() + " =="

        # We want to lottery students by ordering them in some way,
        # giving preference to the students who have so far gotten fewer
        # of their priority classes.  Once the order is established,
        # try adding students until the number of successes is the capacity
        # of the class.
        #
        # Students are likely to have a higher priority reg value when they
        # have fewer classes so far, so sort the students by decreasing reg value.
        users_by_priority = sorted([bundle_priority(r) for r in priority], key=get_val, reverse=True)

        # Now register the students in the order they got sorted.
        # Note: this could alternatively be done by trying to add each user in
        # the list of users who ranked this as priority; they'll all start
        # failing after the class is full. TODO(rye): Figure out if this is
        # actually the way we want to do things.
        registered_count = 0
        cur_index = 0
        while (registered_count < class_cap(sec)) and (cur_index < len(users_by_priority)):
            thisuser = get_user(users_by_priority[cur_index])
            success = try_add(thisuser, sec)
            cur_index += 1

            # If we succeeded, make sure to add one to the registered count.
            if success:
                print thisuser.name() + " (" + thisuser.username + ")"
                registered_count += 1

    # Now print out if there were any issues.  This step apparently takes a while.
    print_issues()


def screwed_sweep_p1_printout(fd=None):
    screwed_sweep_by_type(priority_type, fd)

def screwed_sweep_interested_printout(fd=None):
    screwed_sweep_by_type(interested_type, fd)

def screwed_sweep_by_type(reg_type, fd=None):
    """
    Print out the percentage that each student got, of the priority
    classes that they marked, in order of increasing percentage.
    Also print out, for easy reference, the number of priority classes they
    got out of the total chosen.
    """
    if fd is None: fd = sys.stdout

    def classes_cnt(user):
        classescnt = StudentRegistration.valid_objects().filter(section__parent_class__parent_program=program, user=user, relationship__name=enrolled_type).values('section').distinct().count()
        pcnt = StudentRegistration.valid_objects().filter(section__parent_class__parent_program=program, user=user, relationship__name=reg_type).values('section').distinct().count()
        return (classescnt, pcnt)

    def pclasses_pct(user):
        counts = classes_cnt(user)
        if counts[1] != 0:
            return 100*(counts[0]/(counts[1]*1.0))
        else: return 0

    users = sorted(program.students()['enrolled'], key=pclasses_pct)
    fd.write("Full name,Username,% classes gotten,# received,# applied\n")
    for user in users:
        output = "%s,%s,%d,%d,%d\n" % (user.name(), user.username, pclasses_pct(user), classes_cnt(user)[0], classes_cnt(user)[1])
        fd.write(output.encode('utf-8'))
        

def assign_interesteds():
    """
    Go through all sections that still have space in them, and assign them
    some of the students who were interested in the class.  Start with the
    class with the fewest "interested" markings.

    Phase 4:
    For any classes whose count of interested kids is less than their capacity,
    just fill them up right away.  All other sections are filled in the order
    of number of people interested (increasing).

    Phase 5:
    Similar to phase 2.  Go through all class sections where we didn't assign
    people because there was a conflict over capacity*
    """
    # Function to return the number of people who flagged this class as
    # something they're interested in.  Used for sorting the sections.
    # Actually, this key is changing to a division.
    def interested_count(sec):
        count = StudentRegistration.valid_objects().filter(section=sec, relationship__name=interested_type).values_list('user', flat=True).distinct().count()
        return count/(1.0*class_cap(sec))

    # Filter out all the classes that we filled up in the priority reg stage
    # so we don't worry about them anymore in this stage.
    nonempty_secs = [sec for sec in program.sections().filter(status__gt=0) if not sec.isFull()]

    # Now sort the classes by fewest number of people interested.
    sorted_secs = sorted(nonempty_secs, key=interested_count)

    # In the order of the classes that have the fewest interested
    # people in it (currently, ratio'd with how large they are), 
    # fill up the classes by lottery.
    for sec in sorted_secs:
        print "== Adding interested students to " + sec.emailcode() + ": " + sec.title() + " =="

        # Same procedure as in the case of priority registrations.
        interesteds = StudentRegistration.valid_objects().filter(section=sec, relationship__name=interested_type).values_list('user', flat=True).distinct()
        myusers = ESPUser.objects.filter(id__in=interesteds)
        users_by_val = sorted([bundle_interested(u) for u in myusers], key=get_val, reverse=True)

        # It's easier to, instad of counting, just fill the class till it's
        # full.  If we change to actually using capacity*, this will need to
        # change to have logic similar to the priority registration.
        cur_index = 0
        while not (sec.isFull() or cur_index >= len(users_by_val)):
            thisuser = get_user(users_by_val[cur_index])
            success = try_add(thisuser, sec)
            cur_index += 1

            # If we succeeded, make sure to add one to the registered count.
            if success:
                print thisuser.name() + " (" + thisuser.username + ")"

    # Now print out if there were any issues.  This step apparently takes a while.
    print_issues()


