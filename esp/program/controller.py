from esp.calendar.models import Event, Series
from esp.program.models import Program, Class
from datetime import datetime



def GetCurrentPrograms(time=datetime.now()):
    """ Get all programs that are currently running

    Note that, for a program to be currently running, its top-level """
    return Program.objects.filter(programschedule__event__start__lt=time, programschedule__event__end__gt=time)



