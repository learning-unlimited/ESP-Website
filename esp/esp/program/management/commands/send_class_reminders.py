import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from esp.program.models.class_ import ClassSection, ClassReminder
from esp.program.class_status import ClassStatus
from esp.dbmail.models import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Sends class reminders to students for upcoming classes'

    def handle(self, *args, **options):
        now = timezone.now()
        upcoming_window = now + datetime.timedelta(minutes=45)
        
        # Get sections that have an event starting between now and 45 mins from now
        sections = ClassSection.objects.filter(
            meeting_times__start__gte=now,
            meeting_times__start__lte=upcoming_window,
            status=ClassStatus.ACCEPTED
        ).distinct()

        for section in sections:
            upcoming_events = section.meeting_times.filter(
                start__gte=now, start__lte=upcoming_window
            )
            for event in upcoming_events:
                # Check if reminder already sent for this specific event
                if not ClassReminder.objects.filter(section=section, event=event).exists():
                    # Send reminder
                    students = section.registrations.all()
                    
                    if students.exists():
                        subject = "[Reminder] Upcoming class: %s" % section.parent_class.title
                        rooms = section.prettyrooms()
                        room_str = ", ".join(rooms) if rooms else "Location to be determined"
                        
                        message = "Hello,\n\nThis is a friendly reminder that your class '%s' is starting soon.\n\n" % section.parent_class.title
                        message += "Time: %s\n" % event.start.strftime('%I:%M %p')
                        message += "Location: %s\n\n" % room_str
                        message += "See you there!"
                        
                        student_emails = [student.email for student in students if student.email]
                        if student_emails:
                            # Use dbmail send_mail mechanism 
                            send_mail(
                                subject, 
                                message, 
                                settings.SERVER_EMAIL, # Sender
                                student_emails, 
                                fail_silently=True
                            )
                    
                    # Mark as sent
                    ClassReminder.objects.create(section=section, event=event)
                    self.stdout.write(self.style.SUCCESS("Sent reminders for '%s' at %s" % (section.parent_class.title, event.start)))
