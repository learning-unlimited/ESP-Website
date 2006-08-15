from datetime import datetime, timedelta
from django.shortcuts import render_to_response


def day_after(date):
    """ Return the date + 1 day """
    return date + timedelta(1)

def genCalendar(events, minDate = None, maxDate = None):
    """ Return a Django HttpResponse object containing an HTML blurb, containing a mini-calendar of the listed events

    If the time range is not specified, use the earliest and/or latest events in the given event pool
    """

    # If we aren't given any events, make something sane up to display
    if events.count() < 1:
        minDate = datetime.now()
        maxDate = datetime.now()
    else:
        # If we aren't given a time range, figure out the maximum range for which we have data
        # Note: I don't have a ceil() for days; I'm using floor()+1, which fails if time-of-day == 0
        if minDate != None:
            minDate = events.order_by('start')[0].start

        if maxDate != None:
            maxDate = events.order_by('-end')[0].end

    # Use dates, not datetimes, Because I Can(tm)
    start_date = minDate.date()
    end_date = day_after(maxDate).date()


    if start_date > end_date:
        raise Exception('You\'re starting before you\'re ending.  You can\'t do that!')

    curr_date = start_date

    events_by_day = []

    # Wow, it's an actual valid use for iterators.  But wait, Python doesn't have iterators!  Oh well
    while curr_date <= end_date:
        # Show events from today
        day_events = events.filter(start__range=(curr_date, day_after(curr_date))).order_by('start')
        # Show "ongoing" events: events that start before today but end after the start of today
        continuing_events = events.filter(start__lte=curr_date, end__gt=curr_date).exclude(start__range=(curr_date, day_after(curr_date))).order_by('-end')

        # We're passing the relevant data to the template in the following dictionary format;
        # could replace this with a class without breaking anything, but that seems unnecessary
        events_by_day.append( { 'date': curr_date.strftime('%B %d, %Y'),
                                'continuing_events': continuing_events,
                                'day_events': day_events } )

        curr_date = day_after(curr_date)

    return render_to_response('events/minicalendar', { 'events_by_day': events_by_day } )
