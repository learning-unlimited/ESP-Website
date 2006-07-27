

def program_catalog(request, tl, one, two, module, extra, user_id, prog):
	clas = list(prog.class_set.all().order_by('category'))
	p = one + " " + two
	return render_to_response('program/catalogue', {'Program': p.replace("_", " "), 'courses': clas , 'navbar_list': _makeNavBar(request.path), 'preload_images': preload_images, 'logged_in': user_id, 'tl': tl})

def program_profile(request, tl, one, two, module, extra, user_id, prog):
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
		context['navbar_list'] = _makeNavBar(request.path)
		context['preload_images'] =  preload_images
		return render_to_response('users/profile', context)
	contactInfo = contactInfo[0]

	context['grad'] = contactInfo.graduation_year
	context['studentc'] = regprof.contact_student
	context['emerg'] = regprof.contact_emergency
	context['guard'] = regprof.contact_guardian
	context['navbar_list'] = _makeNavBar(request.path)
	context['preload_images'] =  preload_images
	return render_to_response('users/profile', context)

def program_studentreg(request, tl, one, two, module, extra, user_id, prog):
	if not user_id: return render_to_response('users/login', {'logged_in': False, 'navbar_list': _makeNavBar(request.path), 'preload_images': preload_images})
	curUser = User.objects.filter(id=q)[0]
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
	context['navbar_list'] = _makeNavBar(request.path)
	context['preload_images'] =  preload_images
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

def program_finishstudentreg(request, tl, one, two, module, extra, user_id, prog):
	pass
	

def program_teacherreg(request, tl, one, two, module, extra, user_id, prog):
	if not user_id: return render_to_response('users/pleaselogin', {'logged_in': False, 'navbar_list': _makeNavBar(request.path), 'preload_images': preload_images})
	context = {'logged_in': user_id}
	context['navbar_list'] = _makeNavBar(request.path)
	context['preload_images'] =  preload_images
	context['one'] = one
	context['two'] = two
	context['teacher'] = curUser
	v = GetNode('V/Administer/Program/Class')
	q = prog.anchor
	cobj = UserBit.find_by_anchor_perms(Class, curUser, v, q)
	if cobj == [] or cobj is None:
		cobj = Class()
	else:
		cobj = cobj[0]
		context['class'] = cobj
	ts = list(prog.timeslot_set.all())
	cat = list(ClassCategories.objects.all())
	context['cat'] = cat
	context['ts'] = ts
	return render_to_response('program/teacherreg', context)
	
def program_fillslot(request, tl, one, two, module, extra, user_id, prog):
	ts = TimeSlot.objects.filter(id=extra)[0]
	context = {'logged_in': user_id}
	context['ts'] = ts
	context['one'] = one
	context['two'] = two
	classes = ts.class_set.all()
	
	context['courses'] = classes
	context['navbar_list'] = _makeNavBar(request.path)
	context['preload_images'] =  preload_images
	return render_to_response('program/timeslot', context)
	    
def program_addclass(request, tl, one, two, module, extra, user_id, prog):
	classid = request.POST['class']
	cobj = Class.objects.filter(id=classid)[0]
	cobj.preregister_student(curUser)
	return program(request, tl, one, two, "studentreg")
	    
def program_makeaclass(request, tl, one, two, module, extra, user_id, prog):
	if q is None: return render_to_response('users/login', {'logged_in': False, 'navbar_list': _makeNavBar(request.path), 'preload_images': preload_images})
	for thing in ['title', 'class_info', 'class_size_min', 'class_size_max', 'grade_min', 'grade_max']:
		if not request.POST.has_key(thing) and request.POST[thing].strip() != "":
			return program(request, tl, one, two, "teacherreg", extra = "oops")
	aid = request.POST.get('id', None)
	if aid is None:
		cobj = Class()
	else:
		theclass = Class.objects.filter(id=aid)
		if theclass == [] or theclass is None:
			cobj = Class()
		else:
			cobj = theclass[0]
	title = request.POST['title']
	cobj.grade_max = int(request.POST["grade_max"])
	cobj.grade_min = int(request.POST["grade_min"])
	cobj.class_size_min = int(request.POST['class_size_min'])
	cobj.class_size_max = int(request.POST['class_size_max'])
	cobj.class_info = request.POST['class_info']
	cobj.parent_program = prog
	cobj.anchor = prog.anchor.tree_create(['Classes', "".join(title.split(" "))])
	cobj.anchor.friendly_name = title
	
	cobj.anchor.save()
	v = GetNode( 'V/Administer/Program/Class')
	ub = UserBit()
	ub.user = curUser
	ub.qsc = cobj.anchor
	ub.verb = v
	ub.save()
	timeslot = TimeSlot.objects.filter(id=request.POST['Time'])[0]
	cobj.slot = timeslot
	cat = ClassCategories.objects.filter(id=request.POST['Catigory'])[0]
	cobj.category = cat
	cobj.enrollment = 0
	cobj.save()
	return render_to_response('program/registered', {'logged_in': user_id, 'navbar_list': _makeNavBar(request.path), 'preload_images': preload_images})	    

def program_updateprofile(request, tl, one, two, module, extra, user_id, prog):
	if user_id is None:
		return render_to_response('users/login', {'logged_in': False})
	for thing in ['first', 'last', 'email', 'street', 'guard_name', 'emerg_name', 'emerg_street']:
		if not request.POST.has_key(thing) and request.POST[thing].strip() != "":
			# assert False, 1
			return program(request, tl, one, two, "profile", extra = "oops")
	sphone = False
	gphone = False
	ephone = False
	if request.has_key('dobmonth'):
		if len(request.POST['dobmonth']) not in [1,2]:
			# assert False, 2
			return program(request, tl, one, two, "profile", extra = "oops")
	if request.has_key('dobday'):
		if len(request.POST['dobday']) not in [1,2]:
			# assert False, 3
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
				# assert False, 5
				return program(request, tl, one, two, "profile", extra = "oops")
			sphone = True
	for phone in ['guard_phone_day', 'guard_phone_cell', 'guard_phone_even']:
		if request.POST.has_key(phone) and request.POST[phone].strip() != "":
			aphone = request.POST[phone]
			if aphone.strip() == "None": continue
			aphone = aphone.split("-")
			if len(aphone) != 3 or len(aphone[0]) != 3 or len(aphone[1]) != 3 or len(aphone[2]) != 4:
				# assert False, 6
				return program(request, tl, one, two, "profile", extra = "oops")
			gphone = True
	for phone in ['emerg_phone_day', 'emerg_phone_cell', 'emerg_phone_even']:
		if request.POST.has_key(phone) and request.POST[phone].strip() != "":
			aphone = request.POST[phone]
			if aphone.strip() == "None": continue
			aphone = aphone.split("-")
			if len(aphone) != 3 or len(aphone[0]) != 3 or len(aphone[1]) != 3 or len(aphone[2]) != 4:
				# assert False, 7
				return program(request, tl, one, two, "profile", extra = "oops")
			ephone = True
	if not (sphone and gphone and ephone):
		# assert False, 8
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



program_handlers = {'catalog': program_catalog,
		    'profile': program_profile,
		    'studentreg': program_studentreg,
		    'finishstudentreg': program_finishstudentreg,
		    'teacherreg': program_teacherreg,
		    'fillslot': program_fillslot,
		    'addclass': program_addclass,
		    'makeclass': program_makeclass,
		    'updateprofile': program_updateprofile,
		    }
