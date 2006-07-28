from esp.calendar.models import Event
from esp.dbmail.models import MessageRequest, EmailRequest, EmailController
from esp.users.models import UserBit
from esp.datatree.models import GetNode
from datetime import datetime, timedelta
from django.db.models import Q
from django.contrib.auth.models import User

def send_event_notice(event_start, event_end):
    """ Send event reminders for all events, if any fraction of an event occurs in the given time range.  Send to all users who are subscribed to each event. """
    user_events = { }

    for e in Event.objects.filter(Q(start__range=(event_start, event_end)) | 
                                  Q(end__range=(event_start, event_end)) |
                                  Q(start__lte=event_end, start__gte=event_start, end__lte=event_end, end__gte=event_start)
                                  ):
        print e
        for u in UserBit.bits_get_users(e.anchor, GetNode('V/Subscribe'), now = e.start):
            if not user_events.has_key(u.user.id):
                user_events[u.user.id] = []

            user_events[u.user.id].append(e)
            print 'Appended ' + str(e) + ' to user ' + str(u.user) + ' (' + str(u) + ')'
        print '\n\n\n'

    print user_events

    for user_id in user_events.keys():
        u = User.objects.filter(pk=user_id)[0]
        
        m = MessageRequest()
        m.subject = 'Daily Schedule Digest'
        m.category = None
        m.sender = 'aseering@media.mit.edu'

        m.msgtext = 'Your Schedule Reminders for the day:\n\n' + '='*50 + '\n\n'

        for e in user_events[user_id]:
            m.msgtext += e.short_description + '\n' + e.description + '\n\n' + '-'*50 + '\n\n'

        print "Generated message: " + str(m)
        m.save()

        req = EmailRequest()
        req.target = u
        req.msgreq = m
        req.save()

        print "Generated EmailRequest: " + str(req)

        EmailController().run(m)


def send_event_notices_for_date(day):
    """ Send event reminders for all events that occur in any part on "day" """
    event_start = datetime(day.year, day.month, day.day, 0)
    event_end = datetime(day.year, day.month, day.day, 0) + timedelta(1)

    send_event_notice(event_start, event_end)

def send_event_notices_for_day(day):
    """ Send event notices for either today or tomorrow
    'day' must be one of "today" or "tomorrow"; otherwise "today" is assumed """
    
    if day == 'tomorrow':
        send_event_notices_for_date(datetime.now()+timedelta(1))
    else:
        send_event_notices_for_date(datetime.now())
