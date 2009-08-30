
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from esp.users.models import ContactInfo, UserBit, ESPUser, TeacherInfo, StudentInfo, EducatorInfo, GuardianInfo
from esp.datatree.models import *
from esp.miniblog.models import AnnouncementLink, Entry
from esp.miniblog.views import preview_miniblog
from esp.program.models import Program, RegistrationProfile, ClassSubject
from django.http import Http404, HttpResponseRedirect
#from icalendar import Calendar, Event as CalEvent, UTC
import datetime
from esp.middleware import ESPError
from esp.users.forms.password_reset import UserPasswdForm
from esp.web.util.main import render_to_response
from esp.users.forms.user_profile import StudentProfileForm, TeacherProfileForm, GuardianProfileForm, EducatorProfileForm, UserContactForm
from django.db.models.query import Q



@login_required
def myesp_passwd(request, module):
        """ Change password """
        if request.user.username == 'onsite':
                raise ESPError(False), "Sorry, you're not allowed to change the password of this user. It's special."

        if request.method == "POST":
                form = UserPasswdForm(user=request.user, data=request.POST)
                if form.is_valid():
                        new_data = form.cleaned_data
                        user = authenticate(username=request.user.username,
                                            password=new_data['password'])
                        
                        user.set_password(new_data['newpasswd'])
                        user.save()
                        login(request, user)
                        return render_to_response('users/passwd.html', request, GetNode('Q/Web/myesp'), {'Success': True})
        else:
                form = UserPasswdForm(user=request.user)
                
        return render_to_response('users/passwd.html', request, GetNode('Q/Web/myesp'), {'Problem': False,
                                                    'form': form,
                                                    'Success': False})


def myesp_home(request, module):
	""" Draw the ESP home page """
	curUser = request.user
	sub = GetNode('V/Subscribe')
	entries = Entry.find_posts_by_perms(curUser, sub)
	annlinks = AnnouncementLink.find_posts_by_perms(curUser, sub)
	entries = [x.html() for x in entries.filter(Q(highlight_expire__isnull=True) | Q(highlight_expire__gte=datetime.datetime.now()))]
	annlinks = [x.html() for x in annlinks.filter(Q(highlight_expire__isnull=True) | Q(highlight_expire__gte=datetime.datetime.now()))]
	ann = entries + annlinks
	return render_to_response('display/battlescreen', request, GetNode('Q/Web/myesp'), {'announcements': ann})

#	Format for battlescreens 			Michael P
#	----------------------------------------------
#	The battle screen template is good for drawing individual blocks of helpful stuff.
#	So, it passes the template an array called blocks.

#	Each variable in the blocks array has:
#	-	title
#	-	array of 'header' html strings 
#		(in case you don't want to use separate sections)
#	-	array of sections

#	Each variable in the sections array has
#	-	header text including links
#	-	array of list items
#	-	list of input items
#	-	footer text including links / form items

#	The list item is displayed with a wide cell on the left followed by a narrow cell on the right.
#	The wide cell is like the name of some object to deal with,
#	and the narrow cell is like the administrative actions that can be applied to the object.
#	For example, the wide cell might have "Michael Price: Audio and Speakerbuilding" and the narrow cell
#	might be "Approve / Reject". 

#	An input item is a plain array of 4 containing
#	-	label text
#	-	text value (request.POST[value] = input_text)
#	-	button label (value)
#	-	form action (what URL the data is submitted to)

#	A list item is a plain array of 3 to 5 containing
#	-	left-hand (wide) cell text 
#	-	left-hand (wide) cell url
#	-	right-hand (narrow) cell html
#	-	OPTIONAL: command string
#	-	OPTIONAL: form post URL

#	That hopefully completes the array structure needed for this thing.


def myesp_battlescreen(request, module, admin_details = False, student_version = False):
	"""This function is the main battlescreen for the teachers. It will go through and show the classes
	that they can edit and display. """

	# request.user just got 1-up'd
	currentUser = ESPUser(request.user)

	if request.POST:
		#	If you clicked a button to approve or reject, first clear the "proposed" bit
		#	by setting the end date to now.
		if request.POST.has_key('command'):
			try:
				# not general yet...but started as 'edit','class','classid'...
				command, objtype, objid = request.POST['command'].split('_')
			except ValueError:
				command = None

			if command == 'edit' and objtype == 'class':
				clsid = int(objid) # we have a class
				clslist = list(ClassSubject.objects.filter(id = clsid))
				if len(clslist) != 1:
					assert False, 'Zero (or more than 1) classes match selected ID.'
				clsobj = clslist[0]
				prog = clsobj.parent_program
				two  = prog.anchor.name
				one  = prog.anchor.parent.name
				return program_teacherreg2(request, 'teach', one, two, 'teacherreg', '', prog, clsobj)
	
	# I have no idea what structure this is, but at its simplest level,
	# it's a dictionary
	announcements = preview_miniblog(request)

	usrPrograms = currentUser.getVisible(Program)

	# get a list of editable classes
	if student_version:
		clslist = currentUser.getEnrolledClasses()
	else:
		clslist = currentUser.getEditable(ClassSubject)

	fullclslist = {}
	
	# not the most direct way of doing it,
	# but hey, it's O(n) in class #, which
	# is nice.
	for cls in clslist:
		if fullclslist.has_key(cls.parent_program.id):
			fullclslist[cls.parent_program.id].append(cls)
		else:
			fullclslist[cls.parent_program.id] = [cls]
	
	# I don't like adding this second structure...
	# but django templates made me do it!
	responseProgs = []

	if admin_details:
		admPrograms = currentUser.getEditable(Program).order_by('-id')
	else:
		admPrograms = []
	
	for prog in usrPrograms:
		if not fullclslist.has_key(prog.id):
			curclslist = []
		else:
			curclslist = fullclslist[prog.id]
		responseProgs.append({'prog':        prog,
				      'clslist':     curclslist,
				      'shortened':   False,#len(curclslist) > 5,
				      'totalclsnum': len(curclslist)})

	return render_to_response('battlescreens/general.html', request, GetNode('Q/Web/myesp'), {'page_title':    'MyESP: Teacher Home Page',
								 'progList':      responseProgs,
								 'admin_details': admin_details,
								 'admPrograms'  : admPrograms,
								 'student_version': student_version,
								 'announcements': {'announcementList': announcements[:5],
										   'overflowed':       len(announcements) > 5,
										   'total':            len(announcements)}})


@login_required
def myesp_battlescreen_admin(request, module):
	curUser = ESPUser(request.user)
	if curUser.isAdministrator():
		return myesp_battlescreen(request, module, admin_details = True)
	else:
		raise Http404

@login_required
def myesp_battlescreen_student(request, module):
	curUser = ESPUser(request.user)
	if curUser.isStudent():
		return myesp_battlescreen(request, module, student_version = True)
	else:
		raise Http404


@login_required
def myesp_switchback(request, module):
	user = request.user
	user = ESPUser(user)
	user.updateOnsite(request)

	if not user.other_user:
		raise ESPError(False), 'You were not another user!'

	return HttpResponseRedirect(user.switch_back(request))

@login_required
def edit_profile(request, module):


	curUser = ESPUser(request.user)

	dummyProgram = Program.objects.get(anchor = GetNode('Q/Programs/Dummy_Programs/Profile_Storage'))
	
	if curUser.isStudent():
		return profile_editor(request, None, True, 'student')
	
	elif curUser.isTeacher():
		return profile_editor(request, None, True, 'teacher')
	
	elif curUser.isGuardian():
		return profile_editor(request, None, True, 'guardian')
	
	elif curUser.isEducator():
		return profile_editor(request, None, True, 'educator')	

	else:
		return profile_editor(request, None, True, '')

@login_required
def profile_editor(request, prog_input=None, responseuponCompletion = True, role=''):
    """ Display the registration profile page, the page that contains the contact information for a student, as attached to a particular program """

    from esp.users.models import K12School
    STUDREP_VERB = GetNode('V/Flags/UserRole/StudentRep')
    STUDREP_QSC  = GetNode('Q')


    if prog_input is None:
        prog = Program.objects.get(anchor = GetNode('Q/Programs/Dummy_Programs/Profile_Storage'))
        navnode = GetNode('Q/Web/myesp')
    else:
        prog = prog_input
        navnode = prog

    curUser = request.user
    context = {'logged_in': request.user.is_authenticated() }
    context['user'] = request.user

    curUser = ESPUser(curUser)
    curUser.updateOnsite(request)

    FormClass = {'': UserContactForm,
               'student': StudentProfileForm,
               'teacher': TeacherProfileForm,
               'guardian': GuardianProfileForm,
               'educator': EducatorProfileForm}[role]
    context['profiletype'] = role

    if request.method == 'POST' and request.POST.has_key('profile_page'):
        form = FormClass(curUser, request.POST)

        # Don't suddenly demand an explanation from people who are already student reps
        if UserBit.objects.UserHasPerms(curUser, STUDREP_QSC, STUDREP_VERB):
            if hasattr(form, 'repress_studentrep_expl_error'):
                form.repress_studentrep_expl_error()

        if form.is_valid():
            new_data = form.cleaned_data

            regProf = RegistrationProfile.getLastForProgram(curUser, prog)

            if regProf.id is None:
                old_regProf = RegistrationProfile.getLastProfile(curUser)
            else:
                old_regProf = regProf

            for field_name in ['address_zip','address_city','address_street','address_state']:
                if new_data[field_name] != getattr(old_regProf.contact_user,field_name,False):
                    new_data['address_postal'] = ''

            if new_data['address_postal'] == '':
                new_data['address_postal'] = False

            regProf.contact_user = ContactInfo.addOrUpdate(regProf, new_data, regProf.contact_user, '', curUser)
            regProf.contact_emergency = ContactInfo.addOrUpdate(regProf, new_data, regProf.contact_emergency, 'emerg_')

            if new_data.has_key('dietary_restrictions') and new_data['dietary_restrictions']:
                regProf.dietary_restrictions = new_data['dietary_restrictions']

            # Deal with school entry.
            if new_data.has_key('k12school'):
                if new_data['k12school'] != unicode(K12School.objects.other().id):
                    new_data['school'] = ''

            if role == 'student':
                regProf.student_info = StudentInfo.addOrUpdate(curUser, regProf, new_data)
                regProf.contact_guardian = ContactInfo.addOrUpdate(regProf, new_data, regProf.contact_guardian, 'guard_')
            elif role == 'teacher':
                regProf.teacher_info = TeacherInfo.addOrUpdate(curUser, regProf, new_data)
            elif role == 'guardian':
                regProf.guardian_info = GuardianInfo.addOrUpdate(curUser, regProf, new_data)
            elif role == 'educator':
                regProf.educator_info = EducatorInfo.addOrUpdate(curUser, regProf, new_data)
            blah = regProf.__dict__
            regProf.save()

            curUser.first_name = new_data['first_name']
            curUser.last_name  = new_data['last_name']
            curUser.email     = new_data['e_mail']
            curUser.save()
            if responseuponCompletion == True:
                # prepare the rendered page so it points them to open student/teacher reg's
                ctxt = {}
                if curUser.isStudent() or curUser.isTeacher():
                    userrole = {}
                if curUser.isStudent():
                    userrole['name'] = 'Student'
                    userrole['base'] = 'learn'
                    userrole['reg'] = 'studentreg'
                    regverb = GetNode('V/Deadline/Registration/Student/Classes/OneClass')
                elif curUser.isTeacher():
                    userrole['name'] = 'Teacher'
                    userrole['base'] = 'teach'
                    userrole['reg'] = 'teacherreg'
                    regverb = GetNode('V/Deadline/Registration/Teacher/Classes')
                ctxt['userrole'] = userrole

                progs = UserBit.find_by_anchor_perms(Program, user=curUser, verb=regverb)
                nextreg = UserBit.objects.filter(user__isnull=True, verb=regverb, startdate__gt=datetime.datetime.now()).order_by('startdate')
                ctxt['progs'] = progs
                ctxt['nextreg'] = list(nextreg)
                if len(progs) == 1:
                    return HttpResponseRedirect(u'/%s/%s/%s' % (userrole['base'], progs[0].getUrlBase(), userrole['reg']))
                else:
                    return render_to_response('users/profile_complete.html', request, navnode, ctxt)
            else:
                return True

    else:
        if prog_input is None:
            regProf = RegistrationProfile.getLastProfile(curUser)
        else:
            regProf = RegistrationProfile.getLastForProgram(curUser, prog)
        if regProf.id is None:
            regProf = RegistrationProfile.getLastProfile(curUser)
        new_data = {}
        if curUser.isStudent():
            new_data['studentrep'] = (UserBit.objects.filter(user = curUser,
                                     verb = STUDREP_VERB,
                                     qsc  = STUDREP_QSC).count() > 0)
        new_data['first_name'] = curUser.first_name
        new_data['last_name']  = curUser.last_name
        new_data['e_mail']     = curUser.email
        new_data = regProf.updateForm(new_data, role)
        if request.session.has_key('birth_month') and request.session.has_key('birth_day'):
            new_data['dob'] = datetime.date(1994, int(request.session['birth_month']), int(request.session['birth_day']))
        if request.session.has_key('school_id'):
            new_data['k12school'] = request.session['school_id']

        form = FormClass(curUser, initial=new_data)

	context['request'] = request
	context['form'] = form
	return render_to_response('users/profile.html', request, navnode, context)

@login_required
def myesp_onsite(request, module):
	
	user = ESPUser(request.user)
	if not user.isOnsite():
		raise ESPError(False), 'You are not a valid on-site user, please go away.'
	verb = GetNode('V/Registration/OnSite')
	
	progs = UserBit.find_by_anchor_perms(Program, user = user, verb = verb)

        # Order them decreasing by id
        # - Currently reverse the list in Python, otherwise fbap's cache is ignored
        # TODO: Fix this
        progs = list(progs)
        progs.reverse()

	if len(progs) == 1:
		return HttpResponseRedirect('/onsite/%s/main' % progs[0].getUrlBase())
	else:
		navnode = GetNode('Q/Web/myesp')
		return render_to_response('program/pickonsite.html', request, navnode, {'progs': progs})

@login_required
def myesp_battlescreen_teacher(request, module):
	qscs = UserBit.bits_get_qsc(user=request.user, verb=GetNode("V/Flags/UserRole/Teacher"))
	if qscs.count() > 0:
		return myesp_battlescreen(request, module)
	else:
		raise Http404	


myesp_handlers = {
		   'home': myesp_home,
		   'switchback': myesp_switchback,
		   'onsite': myesp_onsite,
		   'passwd': myesp_passwd,
		   'student': myesp_battlescreen_student,
		   'teacher': myesp_battlescreen_teacher,
		   'admin': myesp_battlescreen_admin,
		   'profile': edit_profile
		   }

