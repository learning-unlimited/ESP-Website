from esp.dbmail.models import send_mail, MessageRequest, TextOfEmail
import time

def send_success_email_to_student(ccc, student_ind, for_real = False):
    student = ccc.students[student_ind]
    from django.conf import settings
    if hasattr(settings, 'EMAILTIMEOUT') and \
           settings.EMAILTIMEOUT is not None:
        timeout = settings.EMAILTIMEOUT
    else:
        timeout = 2
    subject = "[" + ccc.program.niceName() + "] FIXED Schedule"
    from_email = "%s <%s>" % (ccc.program.niceName(), ccc.program.director_email)
    bcc = from_email
    extra_headers = {}
    extra_headers['Reply-To'] = from_email
    text = "<html>\nHello "+student.first_name+",<br /><br />\n\n"
    text += "We've processed your class change request, and have updated your schedule and fixed the errors that were in the last schedule we e-mailed you. Your new schedule is as follows: <br /><br />\n\n"
    text += "%(schedule)s\n\n<br /><br />\n\n"
    if ccc.student_not_checked_in[student_ind]:
        text += "On your first day, you must check in (at room 5-233), turn in your completed medical liability form, and pay the program fee (unless you are a financial aid recipient). After you do this, we will give you the room numbers of your classes.<br /><br />\n\n"
    text += "We're sorry about our previous mistake, and any inconvenience it may have caused.<br /><br />"
    text += "The " + ccc.program.niceName() + " Directors\n"
    text += "</html>"
    text = text.encode('ascii','ignore')
    recipient_list = [student.email, from_email]
    print text%{'schedule':get_better_student_schedule(ccc,student_ind,for_real=False)}
    if for_real:
        send_mail(subject, text%{'schedule':get_better_student_schedule(ccc,student_ind,for_real=True)}, from_email, recipient_list, bcc=bcc, extra_headers=extra_headers)
        time.sleep(timeout)

def get_better_student_schedule(ccc, student_ind, for_real = False):
    """ generate student schedules """
    show_rooms = not (ccc.student_not_checked_in[student_ind] and for_real)
    schedule = "<table border='1'>\n<tr>\n<th>Time%s</th>\n<th>Class and Teacher</th>\n<th>Code</th>\n</tr>\n" % (" and Room" if show_rooms else "")
    sections = list(ccc.students[student_ind].getSections(ccc.program, ["Enrolled"]).distinct())
    sections.sort(key = lambda section: section.meeting_times.order_by('start')[0].start)
    for cls in sections:
        schedule += "<tr>\n<td>"+", ".join(cls.friendly_times())+("<br />"+", ".join(cls.prettyrooms()) if show_rooms else "")+"</td>\n<td>"+cls.title()+"<br />"+", ".join(cls.parent_class.getTeacherNames())+"</td>\n<td>"+cls.emailcode()+"</td>\n</tr>\n"
    schedule += "</table>\n"
    return schedule.encode('ascii','ignore')
