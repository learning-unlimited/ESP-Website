""" Functions needed to transition from single to split class models. """

from esp.program.models.class_ import ClassSubject, ClassSection
from esp.datatree.models import *
from esp.users.models import UserBit
from esp.resources.models import ResourceAssignment

def move_data(subject, section):
    """ This function will only operate on classes created on a code base
    before SVN revision 1475 (when ClassSections were introduced). """
    
    prereg_verb = DataTree.get_by_uri('V/Flags/Registration/Preliminary')
    
    #   Move over userbits
    for ub in UserBit.objects.filter(verb=prereg_verb, qsc=subject.anchor):
        new_ub = ub
        print '-> Moving preregistration for user #%s' % new_ub.user_id
        new_ub.qsc = section.anchor
        new_ub.save()
        
    #   Move meeting times, resources
    for mt in subject.meeting_times.all():
        print '-> Adding meeting time: %s' % mt
        section.meeting_times.add(mt)
    subject.meeting_times.clear()
    for ra in ResourceAssignment.objects.filter(target_subj=subject):
        print '-> Adding resource assignment: %s' % ra
        ra.target = section
        ra.target_subj = None
        ra.save()
    
def transition(class_list):
    
    completed_titles = ['']
    
    for cs in class_list:
        if cs.clsname not in completed_titles:
            completed_titles.append(cs.title())
            print 'Creating a section for class ' + cs.title()
            #   Make the section
            cs.add_default_section()
            sec = cs.default_section()
            sec.status = cs.status
            sec.save()
            
            #   Move data over to that section
            move_data(cs, sec)
            
            #   Find all classes with the same title and make sections out of them!
            other_classes = ClassSubject.objects.filter(anchor__friendly_name=cs.title(), parent_program=cs.parent_program).exclude(id=cs.id)
            for c in other_classes:
                print 'Found copy in class #%d; moving data to new section' % c.id
                new_sec = cs.add_section()
                move_data(c, new_sec)
                c.delete()
        else:
            print 'Skipping over %s' % cs
        

def prog_transition(prog):
    """ Transition the classes of a program over to the new split-model system.
    This will take existing ClassSubjects, make ClassSections for each copy
    found in the database, move registrations and scheduling data into the 
    new sections, and delete all but one of the original ClassSubjects.  
    (Any Classes existing before the upgrade will have silently turned into 
    ClassSubjects.)
    
    Example:
    >>> spark = Program.objects.get(id=18)
    >>> prog_transition(spark)
    """
    cls_list = prog.classes()
    for c in cls_list:
        c.clsname = c.title()
    transition(cls_list)
    
