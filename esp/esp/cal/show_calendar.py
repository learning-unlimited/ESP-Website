from datetime import datetime, timedelta
from django.template import Context, loader


def day_after(date):
    """ Return the date + 1 day """
    return date + timedelta(1)

def day_before(date):
    """ Return the date + 1 day """
    return date - timedelta(1)

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
        if minDate == None:
            minDate = events.order_by('start')[0].start

        if maxDate == None:
            maxDate = events.order_by('-end')[0].end

    # Use dates, not datetimes, Because I Can(tm)
    start_date = minDate.date()
    end_date = day_after(maxDate).date()


    if start_date > end_date:
        raise Exception('You\'re starting before you\'re ending.  You can\'t do that!')

    curr_date = start_date

    events_per_week = { }
    event_weeks = []

    # Wow, it's an actual valid use for iterators.  But wait, Python doesn't have iterators!  Oh well
    while curr_date <= end_date:

        # Show events from today
        day_events = events.filter(start__range=(curr_date, day_after(curr_date))).order_by('start')
        # Show "ongoing" events: events that start before today but end after the start of today
        continuing_events = events.filter(start__lte=curr_date, end__gt=curr_date).order_by('-end')
        print continuing_events

        # We're passing the relevant data to the template in the following dictionary format;
        # could replace this with a class without breaking anything, but that seems unnecessary
        if continuing_events.count() > 0 or day_events.count() > 0:
            events_per_week[str(curr_date.weekday())] = { 'date': curr_date,
                                                          'continuing_events': continuing_events,
                                                          'day_events': day_events } 

        curr_date = day_after(curr_date)

        # If we're moving to a new week, save the old week's events, then clear the event list
        # Yes, this doesn't quite line up right; the last day of the week will be in the wrong week.
        # That's because Python treats Sunday as the last day of the week; we want it to be the first day of the next week
        if curr_date.isocalendar()[1] != day_after(curr_date).isocalendar()[1]:
            event_weeks.append(events_per_week)
            events_per_week = { }
            

    return loader.get_template('events/minicalendar').render(Context( { 'events_by_week': event_weeks } )


def genPlan(events, minDate = None, maxDate = None):
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
        if minDate == None:
            minDate = events.order_by('start')[0].start

        if maxDate == None:
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
        continuing_events = events.filter(start__lte=curr_date, end__gt=curr_date).order_by('-end')

        # We're passing the relevant data to the template in the following dictionary format;
        # could replace this with a class without breaking anything, but that seems unnecessary
        events_by_day.append( { 'date': curr_date.strftime('%B %d, %Y'),
                                'continuing_events': continuing_events,
                                'day_events': day_events } )

        curr_date = day_after(curr_date)

    return loader.get_template('events/minicalendar').render(Context( { 'events_by_week': event_weeks } )

