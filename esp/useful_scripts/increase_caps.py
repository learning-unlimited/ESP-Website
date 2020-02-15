#!/usr/bin/env python2

# Find classes which capacity below the room capacity, and send the teacher an email asking if
# they want to increase their class capacity to the room capacity

from script_setup import *

from esp.dbmail.models import send_mail

program = Program.objects.get(url='Splash/2015')

# TODO: Consider changing this to something non-class-dependent so that the
# emails thread together for admins!
email_subject_template = 'Your Splash class %(email_code)s: "%(title)s"'
email_template = '''
Hi %(teacher_names)s,

Thanks for teaching for Splash!  We've scheduled your class %(email_code)s:
"%(title)s", with capacity %(class_cap)s.  Some of the sections are scheduled in
rooms with more space than that:

%(section_texts)s

Would you be willing to increase the max size of your class to the room size
(or to any amount in between)?  If you would like to do so, please let us know
by replying to this email by 5pm on Wednesday, November 4.  If not, you can
simply ignore this email.

Thanks,
Clio and Mikayla
Splash 2015 Directors
'''
section_template = '%(email_code)s: room %(room)s (capacity %(room_cap)s)'

from_address = 'Splash <splash@mit.edu>'
extra_headers = {
    'Sender': 'server@esp.mit.edu',
}

exclude_class_ids = set([9258, 9316, 9340, 9241])

def listify(l):
    """Convert a list [a,b,c] to text "a, b, and c" or similar."""
    l = list(l)
    if len(l) == 0:
        raise Exception
    if len(l) == 1:
        return l[0]
    if len(l) == 2:
        return ' and '.join(l)
    else:
        l[-1] = 'and ' + l[-1]
        return ', '.join(l)

for c in program.classes():
    if c.id in exclude_class_ids:
        continue
    section_texts = []
    for s in c.sections.all():
        # if the class is scheduled in a room
        if (s.classrooms().exists()
                # if the difference is <= 3, don't bother
                and s.capacity + 3 < s._get_room_capacity()
                # if the class is already big enough that it won't fill, don't
                # bother.  (This number could be higher for Splash.)  This also
                # filters out walk-ins, but we could do that separately if we
                # increased it above 200.
                and s.capacity < 150):
            section_texts.append(section_template % {
                'email_code': s.emailcode(),
                'room': s.initial_rooms()[0].name,
                'room_cap': s._get_room_capacity(),
            })
    if section_texts:
        teacher_names = listify(c.teachers.values_list('first_name', flat=True))
        email_text = email_template % {
            'teacher_names': teacher_names,
            'email_code': c.emailcode(),
            'title': c.title,
            'class_cap': c.class_size_max,
            'section_texts': '\n'.join(section_texts),
        }
        subject = email_subject_template % {
            'email_code': c.emailcode(),
            'title': c.title,
        }
        to_address = '%s-teachers@esp.mit.edu' % c.emailcode()

        while True:
            # this is a while loop because send_mail sometimes errors
            # particularly "too many concurrent SMTP connections"
            # loop until sending is successful,
            # or it errors and the user decides not to retry
            try:
                send_mail(subject, email_text, from_address,
                          [to_address, from_address], extra_headers=extra_headers)
            except Exception as e:
                # print the exception
                print "An error occurred while sending:", subject
                import traceback
                traceback.print_exc()
                # prompt the user to retry
                while True:
                    # loop until the user gives a yes or no answer
                    print "Retry (y/n)?",
                    choice = raw_input().lower()
                    if choice in ['y', 'yes']:
                        retry = True
                        break
                    elif choice in ['n', 'no']:
                        retry = False
                        break
                if retry:
                    continue
                else:
                    print "Skipping:", subject
                    break
            else:
                # email was sent successfully
                print "Sent:", subject
                break
        import time
        time.sleep(1)
