from django.shortcuts import render_to_response
from esp.calendar.models import Event
from esp.web.models import QuasiStaticData
from esp.users.models import ContactInfo
from esp.datatree.models import GetNode
from esp.miniblog.models import Entry
from esp.program.models import RegistrationProfile, TimeSlot, Class
from django.http import HttpResponse, Http404
import datetime

from django.contrib.auth.models import User
from esp.web.models import NavBarEntry

navbar_data = [
	{ 'link': '/teach/what-to-teach.html',
	  'text': 'What You Can Teach',
	'indent': False },
	{ 'link': '/teach/prev-classes.html',
	  'text': 'Previous Classes',
	  'indent': False },
	{ 'link': '/teach/teaching-time.html',
	  'text': 'Time Commitments',
	  'indent': False },
	{ 'link': '/teach/training.html',
	  'text': 'Teacher Training',
	  'indent': False },
	{ 'link': '/teach/ta.html',
	  'text': 'Become a TA',
	  'indent': False },
	{ 'link': '/teach/coteach.html',
	  'text': 'Co-Teach',
	  'indent': False },
	{ 'link': '/teach/reimburse.html',
	  'text': 'Reimbursements',
	  'indent': False },
	{ 'link': '/programs/hssp/teach.html',
	  'text': 'HSSP',
	  'indent': False },
	{ 'link': '/programs/hssp/classreg.html',
	  'text': 'Class Registration',
	  'indent': True },
	{ 'link': '/teach/teacherinformation.html',
	  'text': 'Teacher Information',
	  'indent': True },
	{ 'link': '/programs/hssp/summerhssp.html',
	  'text': 'Summer HSSP',
	  'indent': False },
	{ 'link': '/programs/hssp/classreg.html',
	  'text': 'Class Registration',
	  'indent': True },
	{ 'link': '/programs/firehose/teach.html',
	  'text': 'Firehose',
	  'indent': False },
	{ 'link': '/programs/junction/teach.html',
	  'text': 'JUNCTION',
	  'indent': False },
	{ 'link': '/programs/junction/classreg.html',
	  'text': 'Class Registration',
	  'indent': True },
	{ 'link': '/programs/delve/teach.html',
	  'text': 'DELVE (AP Program)',
	  'indent': False }
]

preload_images = [
	'/media/images/level3/nav/home_ro.gif',
	'/media/images/level3/nav/discoveresp_ro.gif',
	'/media/images/level3/nav/takeaclass_ro.gif',
	'/media/images/level3/nav/volunteertoteach_ro.gif',
	'/media/images/level3/nav/getinvolved_ro.gif',
	'/media/images/level3/nav/archivesresources_ro.gif',
	'/media/images/level3/nav/myesp_ro.gif',
	'/media/images/level3/nav/contactinfo_ro.gif'
]
	  
def index(request):
	# Catherine: This does nothing
	latest_event_list = Event.objects.filter().order_by('-start')
	user_id = request.session.get('user_id', False)
	if user_id != False: user_id = True
	return render_to_response('index.html', {
		'navbar_list': navbar_data,
		'preload_images': preload_images,
		'logged_in': user_id
		})

def bio(request, last, first):
	user_id = request.session.get('user_id', False)
	if user_id != False: user_id = True
	user = User.objects.filter(last_name=last, first_name=first)
	if len(user) < 1: return render_to_response('users/construction', {'logged_in': user_id})
	bio = user[0].teacherbio_set.all()
	if len(bio) < 1: return render_to_response('users/construction', {'logged_in': user_id})
	bio = bio[0].html()
	return render_to_response('learn/bio', {'name': first + " " + last, 'bio': bio, 'logged_in': user_id})

def myesp(request, module):
	user_id = request.session.get('user_id', False)
	if user_id != False: user_id = True
	if module == "register":
		return render_to_response('users/newuser', {'Problem': False,
			'logged_in': user_id})
	if module == "finish":
		for thing in ['confirm', 'password', 'username', 'email', "last_name", "first_name"]:
			if not request.POST.has_key(thing):
				return render_to_response('users/newuser', {'Problem': True,
									  'logged_in': user_id})
		if User.objects.filter(username=request.POST['username']).count() == 0:
			
			if request.POST['password'] != request.POST['confirm']:
				render_to_response('users/newuser', {'Problem': True,
								   'logged_in': user_id})
			if len(User.objects.filter(email=request.POST['email'])) > 0:
				email_user = User.objects.filter(email=request.POST['email'])[0]
				email_user.username = request.POST['username']
				email_user.last_name = request.POST['last_name']
				email_user.first_name = request.POST['first_name']
				email_user.set_password(request.POST['password'])
				email_user.save()
				q = email_user.id
				request.session['user_id'] = q
				return render_to_response('users/regdone', {'logged_in': True})				
			
			django_user = User()
			django_user.username = request.POST['username']
			django_user.last_name = request.POST['last_name']
			django_user.first_name = request.POST['first_name']
			django_user.set_password(request.POST['password'])
			django_user.email = request.POST['email']
			django_user.is_staff = False
			django_user.is_superuser = False
			django_user.save()
			q = django_user.id
			request.session['user_id'] = q
			return render_to_response('users/regdone', {'logged_in': True})
	if module == "emaillist":
		return render_to_response('users/email', {'logged_in': False})

	
	if module == "emailfin":
		if not request.POST.has_key('email'):
			assert False, 1
			return render_to_response('users/newuser', {'Problem': True,
								    'logged_in': user_id})
		if User.objects.filter(email=request.POST['email']).count() == 0:
			if User.objects.filter(email=request.POST['email']).count() > 0:
				return render_to_response('index.html', {
					'navbar_list': _makeNavBar(request.path),
					'preload_images': preload_images,
					'logged_in': False})
			
			email_user = User()
			email_user.email = request.POST['email']
			email_user.is_staff = False
			email_user.is_superuser = False
			email_user.save()
			return render_to_response('index.html', {
				'navbar_list': _makeNavBar(request.path),
				'preload_images': preload_images,
				'logged_in': False})
		
	if module == "signout":
		try: del request.session['user_id']
		except KeyError: pass
		return render_to_response('users/logout', {'logged_in': False})

	if module == "login":
		return render_to_response('users/login', {'logged_in': False})
	if module == "logfin":
		for thing in ['password', 'username']:
			if not request.POST.has_key(thing):
				return render_to_response('users/login', {'Problem': True,
									  'logged_in': user_id})
		curUser = User.objects.filter(username=request.POST['username'])[0]
		if curUser.check_password(request.POST['password']):
			render_to_response('users/login', {'Problem': True,
							   'logged_in': False})
			q = curUser.id
			request.session['user_id'] = q
			return render_to_response('index.html', {
				'navbar_list': _makeNavBar(request.path),
				'preload_images': preload_images,
				'logged_in': True
				})
		else:
			return render_to_response('users/login', {'Problem': True})
	if module == "home":
		q = request.session.get('user_id', None)
		curUser = User.objects.filter(id=q)[0]
		sub = GetNode('V/Subscribe')
		ann = Entry.find_posts_by_perms(curUser, sub)
		ann = [x.html() for x in ann]
		return render_to_response('display/battlescreen', {'announcements': ann, 'logged_in': user_id})
	return render_to_response('users/construction', {'logged_in': user_id})

def qsd(request, url):
	user_id = request.session.get('user_id', False)
	if user_id != False: user_id = True
	try:
		qsd_rec = QuasiStaticData.find_by_url_parts(url.split('/'))
	except QuasiStaticData.DoesNotExist:
		raise Http404
	return render_to_response('qsd.html', {
			'navbar_list': _makeNavBar(request.path),
			'preload_images': preload_images,
			'title': qsd_rec.title,
			'content': qsd_rec.html(),
			'logged_in': user_id})
	     

def redirect(request, tl, one, three):
	Q_Prog = GetNode('Q/Programs')
	try:
		branch = Q_Prog.tree_decode(one.split("/"))
	except DataTree.NoSuchNodeException:
		return qsd(request, one + "/" +three+".html")

	qsd_rec = QuasiStaticData.objects.filter( path = branch, name = tl +  "-" + three )
	if len(qsd_rec) < 1:
		return qsd(request, one + "/" +three+".html")
	return render_to_response('qsd.html', {
		'navbar_list': _makeNavBar(request.path),
		'preload_images': preload_images,
		'title': qsd_rec.title,
		'content': qsd_rec.html(),
		'logged_in': user_id})

def program(request, tl, one, two, module, extra = None):
    q = request.session.get('user_id', False)
    user_id = q
    if user_id != False: user_id = True
    if q is None: return render_to_response('users/login', {'logged_in': False})
    curUser = User.objects.filter(id=q)[0]

    treeItem = "Q/Programs/" + one + "/" + two 
    prog = GetNode(treeItem).program_set.all()
    if len(prog) < 1:
        return render_to_response('users/construction', {'logged_in': user_id})
    prog = prog[0]
    if module == "profile":
	    regprof = RegistrationProfile.objects.filter(user=curUser,program=prog)[0]
	    
	    context = {'logged_in': user_id}
	    context['student'] = curUser
	    context['one'] = one
	    if extra == "oops":
		    context['oops'] = True
	    context['two'] = two
	    context['statenames'] = ['AL' , 'AK' , 'AR', 'AZ' , 'CA' , 'CO' , 'CT' , 'DC' , 'DE' , 'FL' , 'GA' , 'GU' , 'HI' , 'IA' , 'ID'  ,'IL'  ,'IN'  ,'KS'  ,'KY'  ,'LA'  ,'MA' ,'MD'  ,'ME'  ,'MI'  ,'MN'  ,'MO' ,'MS'  ,'MT'  ,'NC'  ,'ND' ,'NE'  ,'NH'  ,'NJ'  ,'NM' ,'NV'  ,'NY' ,'OH'  ,'OK' ,'OR'  ,'PA'  ,'PR' ,'RI'  ,'SC'  ,'SD'  ,'TN' ,'TX'  ,'UT'  ,'VA'  ,'VI'  ,'VT'  ,'WA'  ,'WI'  ,'WV' ,'WY' ,'Canada']
	    contactInfo = curUser.contactinfo_set.all()
	    if len(contactInfo) < 1:
		    empty = ContactInfo()
		    empty.user = curUser
		    context['grad'] = empty
		    context['studentc'] = empty
		    context['emerg'] = empty
		    context['guard'] = empty
		    return render_to_response('users/profile', context)
	    contactInfo = contactInfo[0]

	    context['grad'] = contactInfo.graduation_year
	    context['studentc'] = regprof.contact_student
	    context['emerg'] = regprof.contact_emergency
	    context['guard'] = regprof.contact_guardian
	    return render_to_response('users/profile', context)

    if module == "catalog":
	    treeItem = "Q/Programs/" + one + "/" + two 
	    prog = GetNode(treeItem).program_set.all()
	    if len(prog) < 1:
		    return render_to_response('users/construction', {'logged_in': user_id})
	    prog = prog[0]
	    clas = list(prog.class_set.all().order_by('category'))
	    p = one + " " + two
	    return render_to_response('program/catalogue', {'Program': p.replace("_", " "), 'courses': clas })

    if module == "studentreg":
	    curUser = User.objects.filter(id=q)[0]
	    if q is None: return render_to_response('users/login', {'logged_in': False})
	    regprof = RegistrationProfile.objects.filter(user=curUser,program=prog)
	    if len(regprof) < 1:
		    regprof = RegistrationProfile()
		    regprof.user = curUser
		    regprof.program = prog
	    else:
		    regprof = regprof[0]
	    curUser = User.objects.filter(id=q)[0]
	    context = {'logged_in': user_id}
	    context['program'] = one + " " + two
	    context['program'] = context['program'].replace("_", " ")
	    context['one'] = one
	    context['two'] = two
	    profile_done = False
	    for thing in [regprof.contact_student, regprof.contact_student, regprof.contact_emergency]:
		    foo = validateContactInfo(thing)
		    if foo:
			    profile_done = True
			    break
	    if profile_done: context['profile_graphic'] = "checkmark"
	    else: context['profile_graphic'] = "nocheckmark"
	    context['student'] = curUser.first_name + " " + curUser.last_name
	    ts = list(prog.timeslot_set.all())

	    pre = regprof.preregistered_classes()
	    prerl = []
	    for time in ts:
		    then = [x for x in pre if x.slot == time]
		    if then == []: prerl.append((time, None))
		    else: prerl.append((time, then[0]))
	    context['timeslots'] = prerl

	    if pre != []: context['select_graphic'] = "checkmark"
	    else: context['select_graphic'] = "nocheckmark"
	    
	    regprof.save()
	    return render_to_response('users/studentreg', context)

    if module == "finishstudentreg":
	    pass


    if module == "teacherreg":
	    pass


    if module == "fillslot":
	    ts = TimeSlot.objects.filter(id=extra)[0]
	    context = {'logged_in': user_id}
	    context['ts'] = ts
	    context['one'] = one
	    context['two'] = two
	    classes = ts.class_set.all()
	    context['courses'] = classes
	    return render_to_response('program/timeslot', context)

    if module == "addclass":
	    classid = request.POST['class']
	    cobj = Class.objects.filter(id=classid)[0]
	    cobj.preregister_student(curUser)
	    return program(request, tl, one, two, "studentreg")
    
    if module == "updateprofile":
	    if q is None: return render_to_response('users/login', {'logged_in': False})
	    for thing in ['first', 'last', 'email', 'street', 'guard_name', 'emerg_name', 'emerg_street']:
		    if not request.POST.has_key(thing) and request.POST[thing].strip() != "":
			    assert False, 1
			    return program(request, tl, one, two, "profile", extra = "oops")
	    sphone = False
	    gphone = False
	    ephone = False
	    if request.has_key('dobmonth'):
		    if len(request.POST['dobmonth']) not in [1,2]:
			    assert False, 2
			    return program(request, tl, one, two, "profile", extra = "oops")
	    if request.has_key('dobday'):
		    if len(request.POST['dobday']) not in [1,2]:
			    assert False, 3
			    return program(request, tl, one, two, "profile", extra = "oops")
	    if request.has_key('dobyear'):
		    if len(request.POST['dobyear']) != 4:
			    return program(request, tl, one, two, "profile", extra = "oops")
	    for phone in ['phone_even', 'phone_cell', 'phone_day']:
		    if request.POST.has_key(phone) and request.POST[phone].strip() != "":
			    aphone = request.POST[phone]
			    if aphone.strip() == "None": continue
			    aphone = aphone.split("-")
			    if len(aphone) != 3 or len(aphone[0]) != 3 or len(aphone[1]) != 3 or len(aphone[2]) != 4:
				    assert False, 5
				    return program(request, tl, one, two, "profile", extra = "oops")
			    sphone = True
	    for phone in ['guard_phone_day', 'guard_phone_cell', 'guard_phone_even']:
		    if request.POST.has_key(phone) and request.POST[phone].strip() != "":
			    aphone = request.POST[phone]
			    if aphone.strip() == "None": continue
			    aphone = aphone.split("-")
			    if len(aphone) != 3 or len(aphone[0]) != 3 or len(aphone[1]) != 3 or len(aphone[2]) != 4:
				    assert False, 6
				    return program(request, tl, one, two, "profile", extra = "oops")
			    gphone = True
	    for phone in ['emerg_phone_day', 'emerg_phone_cell', 'emerg_phone_even']:
		    if request.POST.has_key(phone) and request.POST[phone].strip() != "":
			    aphone = request.POST[phone]
			    if aphone.strip() == "None": continue
			    aphone = aphone.split("-")
			    if len(aphone) != 3 or len(aphone[0]) != 3 or len(aphone[1]) != 3 or len(aphone[2]) != 4:
				    assert False, 7
				    return program(request, tl, one, two, "profile", extra = "oops")
			    ephone = True
	    if not (sphone and gphone and ephone):
		    assert False, 8
		    return program(request, tl, one, two, "profile", extra = "oops")
	    curUser = User.objects.filter(id=q)[0]
	    regprof = RegistrationProfile.objects.filter(user__exact=curUser,program__exact=prog)
	    if len(regprof) < 1:
		    regprof = RegistrationProfile()
		    regprof.user = curUser
		    regprof.program = prog
	    else:
		    regprof = regprof[0]
	    curUser.first_name = request.POST['first']
	    curUser.last_name = request.POST['last']
	    curUser.email = request.POST['email']
	    if regprof.contact_student is None:
		    c1 = ContactInfo()
		    c1.user = curUser
		    c1.save()
	    else:
		    c1 = regprof.contact_student
	    c1.grad = request.POST.get('grad', "")
	    c1.e_mail = curUser.email
	    c1.full_name = curUser.first_name + " " + curUser.last_name
	    c1.address_street = request.POST.get('street', "")
	    c1.address_city = request.POST.get('city', "")
	    c1.address_state = request.POST.get('state', "")
	    c1.address_zip = request.POST.get('zip', "")
	    if request.has_key('dobmonth') and request.has_key('dobday') and request.has_key('dobyear'):
		    c1.dob =  datetime.date(int(request.POST['dobyear']), int(request.POST['dobmonth']), int(request.POST['dobday']))
	    c1.phone_day = request.POST.get('phone_day', "")
	    c1.phone_cell = request.POST.get('phone_cell', "")
	    c1.phone_even = request.POST.get('phone_even', "")
	    c1.save()
	    regprof.contact_student = c1	    
	    if regprof.contact_guardian is None:
		    c2 = ContactInfo()
		    c2.user = curUser
		    c2.save()
	    else:
		    c2 = regprof.contact_guardian
	    c2.full_name = request.POST.get('guard_name', "")
	    c2.e_mail = request.POST.get('guard_email', "")
	    q = c2.e_mail
	    p = c2.full_name
	    c2.phone_day = request.POST.get('guard_phone_day', "")
	    c2.phone_cell = request.POST.get('guard_phone_cell', "")
	    c2.phone_even = request.POST.get('guard_phone_even', "")
	    c2.address_street = c1.address_street
	    c2.address_city = c1.address_city
	    c2.address_state = c1.address_state
	    c2.address_zip = c1.address_zip
	    c2.save()
	    regprof.contact_guardian = c2
	    if regprof.contact_emergency is None:
		    c3 = ContactInfo()
		    c3.user = curUser
		    c3.save()
	    else:
		    c3 = regprof.contact_emergency
	    c3.full_name = request.POST.get('emerg_name', "")
	    c3.e_mail = request.POST.get('emerg_email', "")
	    c3.address_street = request.POST.get('emerg_street', "")
	    c3.address_city = request.POST.get('emerg_city', "")
	    c3.address_state = request.POST.get('emerg_state', "")
	    c3.address_zip = request.POST.get('emerg_zip', "")
	    c3.phone_day = request.POST.get('emerg_phone_day', "")
	    c3.phone_cell = request.POST.get('emerg_phone_cell', "")
	    c3.phone_even = request.POST.get('emerg_phone_even', "")
	    c3.save()
	    regprof.contact_emergency = c3	    
	    curUser.save()
	    regprof.save()
	    return program(request, tl, one, two, "studentreg", extra = None)
    return render_to_response('users/construction', {'logged_in': user_id})

def validateContactInfo(ci):
	if ci is None: return False
	if ci.full_name == "" or ci.full_name is None: return False
	if ci.address_street == "" or ci.address_street is None: return False
	if (ci.phone_day != "" and ci.phone_day is not None) or (ci.phone_cell != "" or ci.phone_cell is not None) and not (ci.phone_even != "" or ci.phone_even is not None): return True
	return False

def qsd_raw(request, url):
	user_id = request.session.get('user_id', False)
	if user_id != False: user_id = True
	try:
		qsd_rec = QuasiStaticData.find_by_url_parts(url.split('/'))
	except QuasiStaticData.DoesNotExist:
		raise Http404
	return HttpResponse(qsd_rec.content, mimetype='text/plain')


def _makeNavBar(url):
	urlL = url.split('/')
	urlL = [x for x in urlL if x != '']
	qsdTree = NavBarEntry.find_by_url_parts(urlL)
	navbar_data = []
	for entry in qsdTree:
		qd = {}
		qd['link'] = entry.link
		qd['text'] = entry.text
		qd['indent'] = entry.indent
		navbar_data.append(qd)
	return navbar_data
	
