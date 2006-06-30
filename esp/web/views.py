from django.shortcuts import render_to_response
from esp.calendar.models import Event
#from mysite.polls.models import Poll

def index(request):
	latest_event_list = Event.objects.filter().order_by('-start')
	return render_to_response('index.html')
