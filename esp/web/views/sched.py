from datetime import datetime, timedelta

def draw_calendar(events):
    """ Return the HTML chunk needed to render a calendar """
    try:
        min_date = events.order_by('start')[0].start
        max_date = events.order_by('-end')[0].end

        start_day = datetime(min_date.year, min_date.month, min_date.day, 0, 0, 0)

        

    # Do we really want silent failure?  It deals correctly with events.count()==0
    except Exception:
        return ''
