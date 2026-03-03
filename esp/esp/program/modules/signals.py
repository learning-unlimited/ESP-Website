from django.db.models.signals import post_delete
from django.dispatch import receiver

from esp.program.models import maybe_create_module_ext, StudentRegistration
from esp.program.modules.module_ext import StudentClassRegModuleInfo, ClassRegModuleInfo

# TODO(benkraft): There are actually a lot more modules that depend on these
# module extensions.  In practice it's probably fine because very few programs
# don't have the SCRM and TCRM, but maybe we should have other modules that
# also need these also autocreate them -- there's little harm in doing so.
# Ideally, we might even assert that only those modules access the settings,
# but doing that in practice might be hard.
maybe_create_module_ext('StudentClassRegModule', StudentClassRegModuleInfo)
maybe_create_module_ext('TeacherClassRegModule', ClassRegModuleInfo)


@receiver(post_delete, sender=StudentRegistration)
def promote_waitlisted_student(sender, instance, **kwargs):
    """
    When an 'Enrolled' StudentRegistration is deleted, promote the first
    waitlisted student (by start_date FIFO order) to 'Enrolled' if the
    section has waitlist enabled.
    
    Delegates to ClassSection.promote_from_waitlist() which:
    - Expires the waitlist StudentRegistration
    - Unenrolls the student from conflicting classes in the same timeslot
    - Enrolls the student in this section
    - Sends an email notification
    """
    # Only act if the deleted registration was an 'Enrolled' type
    if instance.relationship.name != 'Enrolled':
        return

    section = instance.section
    program = section.parent_program

    # Check if waitlist is enabled for this program
    try:
        scrmi = program.studentclassregmoduleinfo
        if not scrmi.enable_class_waitlist:
            return
    except StudentClassRegModuleInfo.DoesNotExist:
        return

    # Delegate to the section's promote_from_waitlist method
    # This handles: expiring waitlist reg, dropping conflicts, enrolling, emailing
    section.promote_from_waitlist()
