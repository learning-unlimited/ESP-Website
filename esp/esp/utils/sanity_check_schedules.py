#!/usr/bin/python

def sanity_check_class_overlaps(prog):
    tb_mapping = {}
    retVal = True

    for tb in prog.getClassrooms():
        tb_mapping[tb.id] = False

    for sec in prog.sections():
        for room in sec.classrooms():
            if tb_mapping[room.id]:
                print "Error in class %s:  Time block %s is already taken with class %s" % (sec, time, tb_mapping[time.id])
                retVal = False
            else:
                tb_mapping[room.id] = sec

    return retVal


def sanity_check_clobber_lunch_Spark2010(prog):
    # Lunch in Spark 2010 was from 12pm-1pm or 1pm-2pm; students had to attend one of the two blocks.
    # Therefore, it would be poor form to run a class from 12pm-2pm.

    cls_noon = 427
    cls_1pm = 423

    retVal = True

    for sec in prog.sections():
        meeting_times = set([x.id for x in sec.get_meeting_times()])
        if cls_noon in meeting_times and cls_1pm in meeting_times:
            print "Error in class %s: Class is scheduled over Spark 2010 Lunch" % (sec)
            retVal = False

    return retVal


def sanity_check_teacher_availabilities(prog):
    retVal = True

    for sec in prog.sections():
        meeting_times = sec.get_meeting_times()
        for teacher in sec.teachers:
            available_times = set([x.id for x in teacher.getAvailableTimes(prog)])
            for time in meeting_times:
                if time.id not in available_times:
                    print "Error in class %s, with teacher %s:  Teacher is not available during the class, at time %s" % (sec, teacher, time)
                    retVal = False

    return retVal

def sanity_check_resource_assignments(prog):
    retVal = True

    for sec in prog.sections():
        class_needs_resources = [x.res_type for x in sec.getResourceRequests()]
        for room in sec.classrooms():  # Will almost always only be one room; if it's more than one, we may have a weird case anyway...
            room_has_resources = [x.res_type for x in room.associated_resources()]
            room_has_resids = set([x.id for x in room_has_resources])
            for res in class_needs_resources:
                if res.id not in room_has_resids:
                    print "Error in class %s: ResourceType %s was requested but is not available in room %s" % (sec, res, room)
                    retVal = False

    return retVal


def sanity_check_no_unapproved_classes(prog):
    # If you're at the point of sanity checking a schedule,
    # there shouldn't be any classes left whose status isn't some varity of
    # "approved" or "rejected".
    from esp.program.models import ClassSubject, ClassSection

    retVal = True
    for cls in ClassSubject.objects.filter(parent_program=prog, status=0):  # Just for future-proofing, don't trust prog.students(), etc; in case we decide to have those functions ignore rejected classes or the like
        print "Error in class %s: ClassSubject has been neither approved nor rejected!" % (cls)
        retVal = False

    for sec in ClassSection.objects.filter(parent_class__parent_program=prog).select_related():
        if sec.status != sec.parent_class.status:
            if sec.status < 0 and sec.parent_class.status > 0:
                # We probably approved the class but only want to schedule one of its sections
                print "Warning in class %s: ClassSubject has status %s, but its child Section %s has status %s (this is unusual, but it's ok if you meant to schedule the class but punt one of its sections)" % (sec.parent_class, sec.parent_class.status, sec, sec.status)
            else:
                print "Error in class %s: ClassSubject has status %s, but its child Section %s has status %s (the two statuses should be the same)" % (sec.parent_class, sec.parent_class.status, sec, sec.status)
                retVal = False

    return retVal


def sanity_check_approved_classes_are_scheduled(prog):
    for sec in prog.sections().filter(status__gt=0):
        if len(sec.classrooms()) < 1:
            print "Error in class %s: Section is approved but not scheduled!" % (sec)
    

def sanity_check_schedules(prog):
    checkers = [ sanity_check_class_overlaps,
                 sanity_check_teacher_availabilities,
                 sanity_check_resource_assignments,
                 sanity_check_no_unapproved_classes,
                 sanity_check_approved_classes_are_scheduled,
                 sanity_check_clobber_lunch_Spark2010,
                 ]


    for checker in checkers:
        print "Running check %s..." % (checker.__name__)
        if checker(prog):
            print "Check passed!"
        else:
            print "Check failed!"



