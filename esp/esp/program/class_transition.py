""" Functions needed to transition from single to split class models. """

from esp.program.models.class_ import ClassSubject, ClassSection

def transition():
    for cs in ClassSubject.objects.all():
        print 'Creating a section for class ' + cs.title()
        cs.add_default_section()
    
    
