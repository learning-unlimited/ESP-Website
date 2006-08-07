from esp.qsd.models import QuasiStaticData
from django.contrib.auth.models import User
from esp.users.models import ContactInfo, UserBit
from esp.datatree.models import GetNode, DataTree
from django.shortcuts import render_to_response
from esp.web.navBar import makeNavBar
from esp.web.data import navbar_data, preload_images
from django.http import HttpResponse, Http404, HttpResponseNotAllowed
from esp.qsdmedia.models import Media
from esp.lib.markdownaddons import ESPMarkdown
from esp.settings import MEDIA_ROOT, MEDIA_URL
from os.path import basename, dirname

def qsd_raw(request, url):
	""" Return raw QSD data as a text file """
	try:
		qsd_rec = QuasiStaticData.find_by_url_parts(url.split('/'))
	except QuasiStaticData.DoesNotExist:
		raise Http404

	# aseering 8-7-2006: Add permissions enforcement; Only show the page if the current user has V/Publish on this node
	have_view = UserBit.UserHasPerms( request.user, qsd_rec.path, GetNode('V/Publish') )
	if have_view:
		return HttpResponse(qsd_rec.content, mimetype='text/plain')
	else:
		return Http404
	
def qsd(request, url):
	# Extract URL parts
	url_parts = url.split('/')

	# Detect verb
	url_verb = url_parts.pop()
	url_verb_parts = url_verb.split('.')
	if len(url_verb_parts) > 1:
		url_verb = url_verb_parts.pop()
		other_url = '.'.join(url_verb_parts)
		url_parts.append(other_url)
		other_url = other_url + '.html'
	else:
		url_parts.append(url_verb)
		other_url = url_verb + '.edit.html'
		url_verb = 'read'
	
	# Fetch the QSD object
	try:
		qsd_rec = QuasiStaticData.find_by_url_parts(url_parts)
	except QuasiStaticData.DoesNotExist:
		if url_verb != 'create': raise Http404
		else:
			url_part = url_parts.pop()
			qsd_rec = QuasiStaticData()
			qsd_rec.path = GetNode('Q/Web/' + url_part)
			qsd_rec.name = url_part
			qsd_rec.title = 'New Page'
			qsd_rec.content = 'Please insert your text here'
			qsd_rec.save()

			url_verb = 'edit'

			
	# Detect edit authorizations
	have_edit = UserBit.UserHasPerms( request.user, qsd_rec.path, GetNode('V/Administer') )
	have_read = UserBit.UserHasPerms( request.user, qsd_rec.path, GetNode('V/Publish') )
	

	# Detect the edit verb
	if url_verb == 'edit':
		# Enforce authorizations (FIXME: SHOW A REAL ERROR!)
		if not have_edit: raise Http404

		m = ESPMarkdown(qsd_rec.content, media={})
		m.toString()
		
		# Render an edit form
		return render_to_response('qsd_edit.html', {
			'navbar_list': makeNavBar(request.path),
			'preload_images': preload_images,
			'title': qsd_rec.title,
			'content': qsd_rec.content,
			'missing_files': m.BrokenLinks(),
			'logged_in': request.user.is_authenticated(),
			'target_url': other_url })

	# Detect the standard read verb
	if url_verb == 'read':		
		# Detect POST
		if request.POST.has_key('post_edit'):
			# Enforce authorizations (FIXME: SHOW A REAL ERROR!)
			if not have_edit:
				return HttpResponseNotAllowed(['GET'])
		
			qsd_rec.content = request.POST['content']
			qsd_rec.title = request.POST['title']
			qsd_rec.save()

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

		if not have_read:
			raise Http404

		# Render response
		return render_to_response('qsd.html', {
				'navbar_list': makeNavBar(request.path),
				'preload_images': preload_images,
				'title': qsd_rec.title,
				'content': qsd_rec.html(),
				'logged_in': request.user.is_authenticated(),
				'have_edit': have_edit,
				'edit_url': other_url})
	
	# Operation Complete!
	raise Http404
