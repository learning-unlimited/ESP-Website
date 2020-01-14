import json

class TestProgramManager():
    def __init__(self, client, program, teachers, rooms, timeslots):
        self.client = client
        self.program = program
        self.teachers = teachers
        self.rooms = rooms
        self.timeslots = timeslots
        self.schedule_class_url = '/manage/%s/' % self.program.getUrlBase() + 'ajax_schedule_class'

    def getClassToSchedule(self, section=None, teacher=None, timeslots=None, rooms=None):
        if section == None:
            if teacher == None:
                teacher = self.teachers[0]
            section = teacher.getTaughtSections(self.program)[0]

        if rooms == None:
            rooms = self.rooms[0].identical_resources().filter(event__in=self.timeslots).order_by('event__start')

        if timeslots == None:
            timeslots = self.program.getTimeSlots().order_by('start')

        return (section, timeslots, rooms)

    #schedule class,
    #NO guarantee that it's a class that hasn't been scheduled yet
    #return a tuple (section, times, rooms)
    def scheduleClass(self, section=None, teacher=None, timeslots=None, rooms=None):
        #choose section, times, and rooms
        (section, timeslots, rooms) = self.getClassToSchedule(section=section, teacher=teacher, timeslots=timeslots, rooms=rooms)

        #schedule the class
        blocks = '\n'.join(['%s,%s' % (r.event.id, r.identical_id()) for r in rooms[0:2]])
        response = self.client.post(self.schedule_class_url, {'action': 'assignreg', 'cls': section.id, 'block_room_assignments': blocks, 'override': 'false'})
        assert response.status_code == 200

        #make sure the scheduling had the expected result
        success = json.loads(response.content)['ret']

        #return information about the class we tried to schedule
        return (section, timeslots, rooms, success)

    def unschedule_class(self, section_id):
        resp = self.client.post(self.schedule_class_url, {'action': 'deletereg', 'cls': section_id})
        assert resp.status_code == 200 #successful deleting of class
