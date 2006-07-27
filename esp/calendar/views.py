def iCalFeed(request):
	""" Creates an iCal calendar file based on the Events table """
	cal = Calendar()
	cal.add('version', '2.0')

	for e in Event.objects.all():
		cal_event = CalEvent()
		cal_event.add('summary', e.short_description)
		cal_event.add('description', e.description)
		cal_event.add('dtstart', e.start)
		cal_event.add('dtend', e.end)
		cal.add_component(cal_event)

	return cal.as_string()
