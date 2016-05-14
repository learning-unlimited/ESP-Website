from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.utils.web import render_to_response
from esp.cal.models import Event, EventType
from esp.users.models import UserAvailability
from esp.program.modules.forms.teacherevents import TimeslotForm


class AdminTeacherEventsModule(ProgramModuleObj):
    # General Info functions
    @classmethod
    def module_properties(cls):
        return {
            "module_type": "manage",
            'required': False,
            'admin_title': 'Manage Teacher Training and Interviews',
            'link_title': 'Teacher Training and Interviews',
        }


    def entriesBySlot(self, event):
        return UserAvailability.objects.filter(event=event)

    @main_call
    @needs_admin
    def teacher_events(self, request, tl, one, two, module, extra, prog):
        context = {}

        if request.method == 'POST':
            data = request.POST

            if data['command'] == 'delete':
                #   delete timeslot
                ts = Event.objects.get(id=data['id'])
                ts.delete()

            elif data['command'] == 'add':
                #   add/edit timeslot
                form = TimeslotForm(data)
                if form.is_valid():
                    new_timeslot = Event()

                    # decide type
                    type = "training"

                    if data.get('submit') == "Add Interview":
                        type = "interview"

                    form.save_timeslot(self.program, new_timeslot, type)
                else:
                    context['timeslot_form'] = form

        if 'timeslot_form' not in context:
            context['timeslot_form'] = TimeslotForm()

        interview_times = self.program.get_teacher_event_times('interview')
        training_times = self.program.get_teacher_event_times('training')

        for ts in list(interview_times) + list(training_times):
            ts.teachers = [x.user.first_name + ' ' + x.user.last_name + ' <' + x.user.email + '>' for x in self.entriesBySlot(ts)]

        context['prog'] = prog
        context['interview_times'] = interview_times
        context['training_times'] = training_times

        return render_to_response(self.baseDir()+'teacher_events.html', request, context)

    class Meta:
        proxy = True
        app_label = 'modules'
