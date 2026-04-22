import datetime
from collections import defaultdict

from django import template

from esp.cal.models import Event

register = template.Library()


@register.simple_tag
def classes_by_day(classes):
    """
    Expand a list of ClassSections (and compulsory Event objects) into
    per-day schedule entries for multi-week programs.

    For classes that meet on only one calendar date, yields a single entry.
    For classes that meet on multiple distinct calendar dates (repeating /
    multi-week classes), yields one entry per distinct date so that the
    schedule shows the class once per week.

    Activated in studentschedule.tex when the TagDict tag
    ``multiweek_schedule`` is set on the program.

    Returns a list of dicts sorted by meeting start time:
      cls          -- the ClassSection (or Event for compulsory blocks)
      event        -- the specific Event representing this day's occurrence
      day_time     -- human-readable time string for this occurrence,
                      always including the date (e.g. "Sat, Oct 05, 10am--12pm")
      is_repeating -- True when the class spans multiple distinct calendar dates
    """
    rows = []

    for cls in classes:
        # Compulsory timeslot -- an Event injected directly by the view
        if isinstance(cls, Event):
            rows.append({
                'cls': cls,
                'event': cls,
                'day_time': cls.pretty_time(include_date=True),
                'is_repeating': False,
            })
            continue

        meeting_times = list(cls.meeting_times.all())

        if not meeting_times:
            rows.append({
                'cls': cls,
                'event': None,
                'day_time': '',
                'is_repeating': False,
            })
            continue

        # Group events by calendar date to detect repeating classes
        by_date = defaultdict(list)
        for event in meeting_times:
            by_date[event.start.date()].append(event)

        is_repeating = len(by_date) > 1

        if is_repeating:
            # Yield one row per week; collapse same-day events into one time string
            for date in sorted(by_date.keys()):
                day_events = sorted(by_date[date], key=lambda e: e.start)
                collapsed = Event.collapse(day_events, tol=datetime.timedelta(minutes=15))
                day_time = ', '.join(
                    e.pretty_time(include_date=True) for e in collapsed
                )
                rows.append({
                    'cls': cls,
                    'event': day_events[0],
                    'day_time': day_time,
                    'is_repeating': True,
                })
        else:
            first_event = min(meeting_times, key=lambda e: e.start)
            rows.append({
                'cls': cls,
                'event': first_event,
                'day_time': ', '.join(cls.friendly_times(include_date=True)),
                'is_repeating': False,
            })

    rows.sort(key=lambda r: (0, r['event'].start) if r['event'] else (1,))
    return rows
