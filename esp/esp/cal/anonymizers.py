from esp.cal.models import EventType, Event, EmailReminder
from anonymizer import Anonymizer

class EventTypeAnonymizer(Anonymizer):

    model = EventType

    attributes = [
        ('id', "SKIP"),
        ('description', "lorem"),
    ]


class EventAnonymizer(Anonymizer):

    model = Event

    attributes = [
        ('id', "SKIP"),
        ('start', "datetime"),
        ('end', "datetime"),
        ('short_description', "lorem"),
        ('description', "lorem"),
        ('name', "name"),
        ('program_id', "SKIP"),
        ('event_type_id', "SKIP"),
        ('priority', "integer"),
    ]


class EmailReminderAnonymizer(Anonymizer):

    model = EmailReminder

    attributes = [
        ('id', "SKIP"),
        ('event_id', "SKIP"),
        ('email_id', "SKIP"),
        ('date_to_send', "datetime"),
        ('sent', "bool"),
    ]
