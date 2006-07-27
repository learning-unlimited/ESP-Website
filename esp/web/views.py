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
	
	# Detect edit authorizations
	if user_id:
		user = User.objects.filter(id=user_id)[0]
	else:
		user = None
	have_edit = UserBit.UserHasPerms( user, qsd_rec.path, GetNode('V/Administer') )

	# FIXME: the create verb is NOT implemented

	# Detect the edit verb
	if url_verb == 'edit':
		# Enforce authorizations (FIXME: SHOW A REAL ERROR!)
		if not have_edit: raise Http404
		
		# Render an edit form
		return render_to_response('qsd_edit.html', {
			'navbar_list': _makeNavBar(request.path),
			'preload_images': preload_images,
			'title': qsd_rec.title,
			'content': qsd_rec.content,
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
				'navbar_list': _makeNavBar(request.path),
				'preload_images': preload_images,
				'title': qsd_rec.title,
				'content': qsd_rec.html(),
				'logged_in': logged_in,
				'have_edit': have_edit,
				'edit_url': other_url})
	
	# Operation Complete!
	raise Http404
