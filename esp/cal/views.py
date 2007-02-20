from esp.calendar.models import Event
from esp.web.util import render_to_response
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django import forms
import icalendar


def createevent(request):
        """ Create an Event, via a Web form """
        # aseering 8-9-2006: Code blatantly copied from http://www.djangoproject.com/documentation/forms/; see that page for reference                
        manipulator = Event.AddManipulator()

	# If we're POSTed to, we're trying to receive an update
        if request.POST:
                POSTdata = request.POST.copy()
	
		# Official Django error checker; checks for error conditions as specified in the model

                errors = manipulator.get_validation_errors(POSTdata)

                # If there aren't any errors, save the event

		if not errors:
                        manipulator.do_html2python(POSTdata)
                        new_event = manipulator.save(POSTdata)


                        return HttpResponseRedirect('/events/edit/?%i', new_event.id)

        # Otherwise, generate a blank new-page form
        else:
                errors = POSTdata = {}

        form = forms.FormWrapper(manipulator, POSTdata, errors)
	return render_to_response('events/create_update', request, GetNode('Q/Web'), {'form': form } )


def updateevent(request, id=None):
        """ Update an Event, via a Web form """
        # aseering 8-9-2006: Code blatantly copied from myesp_createevnt; see that function for reference
        manipulator = Event.ChangeManipulator(id)


	# We don't have a generic list page yet; work on that
	if id == None:
		raise Http404
	
	# If we're POSTed to, we're trying to receive an update
        elif request.POST:
                POSTdata = request.POST.copy()

                # Official Django error checker; checks for error conditions as specified in the model
                errors = manipulator.get_validation_errors(POSTdata)

                # If there aren't any errors, save the event
                if not errors:
                        manipulator.do_html2python(POSTdata)
                        new_event = manipulator.save(POSTdata)


                        return HttpResponseRedirect('/events/edit/?%i', new_event.id)

        # Otherwise, generate a blank new-page form
        else:
                errors = POSTdata = {}

        form = forms.FormWrapper(manipulator, POSTdata, errors)
	return render_to_response('events/create_update', request, GetNode('Q/Web'), {'form': form } )


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
