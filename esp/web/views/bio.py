
from esp.users.models     import ESPUser
from esp.program.models   import TeacherBio, Program, ArchiveClass
from esp.web.util         import get_from_id, render_to_response
from esp.datatree.models  import GetNode
from django               import forms
from django.http          import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from esp.middleware       import ESPError

@login_required
def bio_edit(request, tl, last, userid, progid = None, external = False):
	""" Edits a teacher bio """
	from esp.web.manipulators import TeacherBioManipulator

	
	founduser    = get_from_id(userid, ESPUser, 'user')

	if request.user.id != founduser.id and request.user.is_staff != True:
		raise ESPError(False), 'You are not authorized to edit this biography.'
		
	
	foundprogram = get_from_id(progid, Program, 'program', False)

	lastbio      = TeacherBio.getLastBio(founduser)
		
	
	manipulator = TeacherBioManipulator()

	

	# if we submitted a newly edited bio...
	if request.method == 'POST' and request.POST.has_key('bio_submitted'):
		new_data = request.POST.copy()
		new_data.update(request.FILES) # Add any files that exist

		manipulator.prepare(new_data) # make any form changes

		
		errors = manipulator.get_validation_errors(new_data)

		if not errors:
			if foundprogram is not None:
				# get the last bio for this program.
				progbio = TeacherBio.getLastForProgram(founduser, foundprogram)


			# the slug bio and bio
			progbio.slugbio  = new_data['slugbio']
			progbio.bio      = new_data['bio']
			
			progbio.save()
			# save the image
			if new_data.has_key('picture'):
				progbio.save_picture_file(new_data['picture']['filename'], new_data['picture']['content'])
			else:
				progbio.picture = lastbio.picture
				progbio.save()
			if external:
				return True
			return HttpResponseRedirect(progbio.url())
		
	else:
		errors = {}
		new_data = {}

		new_data['slugbio']      = lastbio.slugbio
		new_data['bio']          = lastbio.bio
		new_data['picture_file'] = lastbio.picture
		
	return render_to_response('users/teacherbioedit.html', request, GetNode('Q/Web/Bio'), {'form':    forms.FormWrapper(manipulator, new_data, errors),
											       'user':    founduser,
											       'picture_file': lastbio.picture})

	
	

def bio(request, tl, last, userid):
	""" Displays a teacher bio """
	
	founduser = get_from_id(userid, ESPUser, 'user')

	bio = TeacherBio.getLastBio(founduser)
	if bio.picture is None:
		bio.picture = 'not-available.jpg'
		
	if bio.slugbio is None:
		bio.slugbio = 'ESP Teacher'
	if bio.bio     is None:
		bio.bio     = 'Not Available.'


	classes = ArchiveClass.getForUser(founduser)

	return render_to_response('users/teacherbio.html', request, GetNode('Q/Web/Bio'), {'user': founduser,
											   'bio': bio,
											   'classes': classes})
