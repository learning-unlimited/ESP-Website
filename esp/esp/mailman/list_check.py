from esp.mailman import list_members
from esp.users.models import ESPUser, User
from esp.users.models.userbits import *
from esp.program.models.class_ import *
import re

#These 4 methods determine who the website thinks should be on a given list
def get_teachers_by_class(class_string):
    cls = ClassSubject.objects.get(anchor__name=class_string.upper())
    return cls.teachers()

def get_teachers_by_section(section_string):
    class_string,num = section_string.rsplit('s')
    section = ClassSection.objects.get(anchor__parent__name=class_string.upper(),anchor__name="Section"+num)
    return section.teachers
    #for whatever reason, sections have teachers as a property, 
    #not a method like classes. it just calls teachers on the parent class

def get_students_by_class(class_string):
    cls = ClassSubject.objects.get(anchor__name=class_string.upper())
    return cls.students()

def get_students_by_section(section_string):
    class_string,num = section_string.rsplit('s')
    section = ClassSection.objects.get(anchor__parent__name=class_string.upper(),anchor__name="Section"+num)
    return section.students()

def list_compare(list_name):
    """Given the name of a teacher, section teacher , student class, or student section list, compare the list of email on the mailman list to the website accounts that should be on it"""

    #find what mailman thinks:
    mailman_list=list_members(list_name)

    #find what website thinks
    if list_name.endswith("-teachers"):
        if re.match("[a-zA-Z]\d+s\d+",list_name[:-9]):
            website_list=get_teachers_by_section(list_name[:-9])
        else:
            website_list=get_teachers_by_class(list_name[:-9])
    elif list_name.endswith("-students"):
        #determine if whole class, or section
        if re.match("[a-zA-Z]\d+s\d+",list_name[:-9]):
            website_list=get_students_by_section(list_name[:-9])
        else:
            website_list=get_students_by_class(list_name[:-9])
    else: #not one of the above types of lists
        return

    MM_not_website=[x for x in mailman_list if x not in website_list]
    website_not_MM=[x for x in website_list if x not in mailman_list]

    if len(MM_not_website)+len(website_not_MM) == 0: return
    print "In MM but not website",MM_not_website
    print "In website but not MM",website_not_MM    
