from esp.calendar.models import Event
from esp.dbmail.models import MessageRequest, EmailRequest, EmailController
from esp.users.models import UserBit
from esp.datatree.models import GetNode

def send_event_notice(event_start, event_end):
    """ Send event reminders for all events, if any fraction of an event occurs in the given time range.  Send to all users who are subscribed to each event. """
    user_events = { }

    for e in Event.objects.filter(Q(start__range=(event_start, event_end)) | 
                                  Q(end__range=(event_start, event_end))
                                  )):
        for u in UserBit.bits_get_users(e.anchor, GetNode('V/Subscribe'), now = e.start):
            if not user_events.has_key(u.user):
                user_events[u.user] = []

            user_events[u.user].append(e)

    for u in user_events.keys():
        m = MessageRequest()
        m.subject = 'Daily E-mail Digest'
        m.category = None
        m.sender = 'noreply@mit.edu'

        m.msgtext = ''

        for e in user_events[u.user]:
            m.msgtext += e.short_description + '\n' + e.description + '\n\n'

        m.save()

        req = EmailRequest()
        req.target = u.user
        req.msgreq = m
        req.save()

        EmailController.run(m)
