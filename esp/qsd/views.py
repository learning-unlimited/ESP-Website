from esp.qsd.models import QuasiStaticData
from django.contrib.auth.models import User
from esp.users.models import ContactInfo, UserBit, GetNodeOrNoBits
from esp.datatree.models import GetNode, DataTree
from django.shortcuts import render_to_response
from esp.web.navBar import makeNavBar
from esp.web.data import navbar_data, preload_images
from django.http import HttpResponse, Http404, HttpResponseNotAllowed
from esp.qsdmedia.models import Media
from esp.lib.markdownaddons import ESPMarkdown
from esp.settings import MEDIA_ROOT, MEDIA_URL
from os.path import basename, dirname

#def qsd_raw(request, url):
#	""" Return raw QSD data as a text file """
#	try:
#		qsd_rec = QuasiStaticData.find_by_url_parts(GetNode('Q/Web'),url.split('/'))
#	except QuasiStaticData.DoesNotExist:
#		raise Http404
#
#	# aseering 8-7-2006: Add permissions enforcement; Only show the page if the current user has V/Publish on this node
#	have_view = UserBit.UserHasPerms( request.user, qsd_rec.path, GetNode('V/Publish') )
#	if have_view:
#		return HttpResponse(qsd_rec.content, mimetype='text/plain')
#	else:
#		return Http404
	
def qsd(request, branch, url_name, url_verb, base_url):
	# Detect edit authorizations
	have_edit = UserBit.UserHasPerms( request.user, branch, GetNode('V/Administer/Edit') )
	have_read = UserBit.UserHasPerms( request.user, branch, GetNode('V/Flags/Public') )

	# Fetch the QSD object
	try:
		qsd_recs = QuasiStaticData.objects.filter( path = branch, name = url_name ).order_by('-create_date')
		if qsd_recs.count() < 1:
			raise QuasiStaticData.DoesNotExist

		qsd_rec = qsd_recs[0]

	except QuasiStaticData.DoesNotExist:
		if have_edit:
			#and ( url_verb == 'edit' ):
			qsd_rec = QuasiStaticData()
			qsd_rec.path = branch
			qsd_rec.name = url_name
			qsd_rec.title = 'New Page'
			qsd_rec.content = 'Please insert your text here'

			url_verb = 'edit'
		else:
			assert False, 'Could not find QSD entry'
			raise Http404

	if url_verb == 'create':
		qsd_rec.save()
		url_verb = 'edit'
			
	# Detect POST
	if request.POST.has_key('post_edit'):
		# Enforce authorizations (FIXME: SHOW A REAL ERROR!)
		if not have_edit:
			return HttpResponseNotAllowed(['GET'])
		
		qsd_rec_new = QuasiStaticData()
		qsd_rec_new.path = branch
		qsd_rec_new.name = url_name
		qsd_rec_new.author = request.user
		qsd_rec_new.content = request.POST['content']
		qsd_rec_new.title = request.POST['title']
		qsd_rec_new.save()

		qsd_rec = qsd_rec_new

		# If any files were uploaded, save them
		for FILE in request.FILES.keys():
			m = Media()

			# Strip "media/" from FILE, and strip the file name; just return the path
			path = dirname(FILE[6:])
			if path == '':
				m.anchor = qsd_rec.path
			else:
				m.anchor = GetNode('Q/' + dirname(FILE))
				
			m.mime_type = request.FILES[FILE]['content-type']
			# Do we want a better/manual mechanism for setting friendly_name?
			m.friendly_name = basename(FILE)
			m.size = len(request.FILES[FILE]['content'])
			
			splitname = basename(FILE).split('.')
			if len(splitname) > 1:
				m.file_extension = splitname[-1]
			else:
				m.file_extension = ''

			m.format = ''

			local_filename = FILE
			if FILE[:6] == 'media/':
				local_filename = FILE[6:]
					
			m.save_target_file_file(local_filename, request.FILES[FILE]['content'])
			m.save()


	# Detect the edit verb
	if url_verb == 'edit':
		# Enforce authorizations (FIXME: SHOW A REAL ERROR!)
		if not have_edit:
			assert False, 'Insufficient permissions for QSD edit'
			raise Http404

		m = ESPMarkdown(qsd_rec.content, media={})
		m.toString()
		
		# Render an edit form
		return render_to_response('qsd_edit.html', {
			'request': request,
			'navbar_list': makeNavBar(request.user, branch),
			'preload_images': preload_images,
			'title': qsd_rec.title,
			'content': qsd_rec.content,
			'qsdrec': qsd_rec,
			'missing_files': m.BrokenLinks(),
			'logged_in': request.user.is_authenticated(),
			'target_url': base_url.split("/")[-1] + ".edit.html",
			'return_to_view': base_url.split("/")[-1] + ".html" })

	# Detect the standard read verb
	if url_verb == 'read':		
		if not have_read:
			assert False, 'Insufficient permissions for QSD read'
			raise Http404

		# Render response
		return render_to_response('qsd.html', {
			'request': request,
			'navbar_list': makeNavBar(request.user, branch),
			'preload_images': preload_images,
			'title': qsd_rec.title,
			'content': qsd_rec.html(),
			'qsdrec': qsd_rec,
			'logged_in': request.user.is_authenticated(),
			'have_edit': have_edit,
			'edit_url': base_url + ".edit.html" })
	
	# Operation Complete!
	assert False, 'Unexpected QSD operation'
       	raise Http404
