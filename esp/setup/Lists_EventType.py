from esp.calendar.models import EventType

EventTypes = (
    'Program',
    'Social Activity',
    )

for e_desc in EventTypes:
    if EventType.objects.filter(description=e).count() == 0:
        e = EventType()
        e.description = e_desc
        e.save()

