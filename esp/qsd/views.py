from esp.qsd.models import QuasiStaticData
from django.contrib.auth.models import User
from esp.users.models import ContactInfo, UserBit
from esp.datatree.models import GetNode
from django.shortcuts import render_to_response
from esp.web.navBar import makeNavBar
from esp.web.data import navbar_data, preload_images
from django.http import HttpResponse, Http404, HttpResponseNotAllowed
from esp.lib.markdownaddons import ESPMarkdown

def qsd_raw(request, url):
	user_id = request.session.get('user_id', False)
	if user_id != False: user_id = True
	try:
		qsd_rec = QuasiStaticData.find_by_url_parts(url.split('/'))
	except QuasiStaticData.DoesNotExist:
		raise Http404
	return HttpResponse(qsd_rec.content, mimetype='text/plain')

def qsd(request, url):
	# Fetch user login state
	user_id = request.session.get('user_id', False)
	logged_in = user_id
	if logged_in != False: logged_in = True

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
	if user_id:
		user = User.objects.filter(id=user_id)[0]
	else:
		user = None
	have_edit = UserBit.UserHasPerms( user, qsd_rec.path, GetNode('V/Administer') )

	# Detect the edit verb
	if url_verb == 'edit':
		# Enforce authorizations (FIXME: SHOW A REAL ERROR!)
		if not have_edit: raise Http404

		m = ESPMarkdown(qsd_rec.content, media={})
		
		# Render an edit form
		return render_to_response('qsd_edit.html', {
			'navbar_list': makeNavBar(request.path),
			'preload_images': preload_images,
			'title': qsd_rec.title,
			'content': qsd_rec.content,
			'missing_files': m.BrokenLinks(),
			'logged_in': logged_in,
			'target_url': other_url })
			
	# Detect the standard read verb
	if url_verb == 'read':
		# Detect POST
		if request.POST.has_key('post_edit'):
			# Enforce authorizations (FIXME: SHOW A REAL ERROR!)
			if not have_edit: return HttpResponseNotAllowed(['GET'])
		
			qsd_rec.content = request.POST['content']
			qsd_rec.title = request.POST['title']
			qsd_rec.save()

		# Render response
		return render_to_response('qsd.html', {
				'navbar_list': makeNavBar(request.path),
				'preload_images': preload_images,
				'title': qsd_rec.title,
				'content': qsd_rec.html(),
				'logged_in': logged_in,
				'have_edit': have_edit,
				'edit_url': other_url})
	
	# Operation Complete!
	raise Http404
