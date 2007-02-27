from esp.qsd.models import QuasiStaticData
from django.contrib.auth.models import User
from esp.users.models import ContactInfo, UserBit, GetNodeOrNoBits
from esp.datatree.models import GetNode, DataTree
from esp.web.views.navBar import makeNavBar
from esp.web.util.main import navbar_data, preload_images, render_to_response
from django.http import HttpResponse, Http404, HttpResponseNotAllowed
from esp.qsdmedia.models import Media
from esp.lib.markdownaddons import ESPMarkdown
from esp.settings import MEDIA_ROOT, MEDIA_URL
from os.path import basename, dirname
from datetime import datetime
from django.core.cache import cache
from esp.dblog.views import ESPError
from django.template.defaultfilters import urlencode

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

def qsd(request, branch, section, url_name, url_verb, base_url):

	# Pages are global per-user (not unique per-user)
	cache_id = str(branch.id) + ':' + str(url_name)

	# Detect edit authorizations
	have_edit = UserBit.UserHasPerms( request.user, branch, GetNode('V/Administer/Edit') )
	have_read = UserBit.UserHasPerms( request.user, branch, GetNode('V/Flags/Public') )

	# Fetch the QSD object
	try:
		cache_qsd = cache.get(urlencode('quasistaticdata:' + cache_id))
		if cache_qsd != None:
			qsd_rec = cache_qsd
		else:			
			qsd_recs = QuasiStaticData.objects.filter( path = branch, name = url_name ).order_by('-create_date')
			if qsd_recs.count() < 1:
				raise QuasiStaticData.DoesNotExist

			qsd_rec = qsd_recs[0]

			cache.set(urlencode('quasistaticdata:' + cache_id), qsd_rec)

	except QuasiStaticData.DoesNotExist:
		if have_edit and (url_verb == 'edit' or url_verb == 'create'):
			qsd_rec = QuasiStaticData()
			qsd_rec.path = branch
			qsd_rec.name = url_name
			qsd_rec.title = 'New Page'
			qsd_rec.content = 'Please insert your text here'
			qsd_rec.create_date = datetime.now()

			url_verb = 'edit'
		else:
			raise Http404

	if url_verb == 'create':
		#qsd_rec.save()
		url_verb = 'edit'
			
	# Detect POST
	if request.POST.has_key('post_edit'):
		# Enforce authorizations (FIXME: SHOW A REAL ERROR!)
		if not have_edit:
			return ESPError("You don't have permission to edit this page.", log_error = False)
		
		qsd_rec_new = QuasiStaticData()
		qsd_rec_new.path = branch
		qsd_rec_new.name = url_name
		qsd_rec_new.author = request.user
		qsd_rec_new.content = request.POST['content']
		qsd_rec_new.title = request.POST['title']
		qsd_rec_new.create_date = datetime.now()
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

		cache.delete(urlencode('quasistaticdata:' + cache_id))
		cache.delete(urlencode('quasistaticdata_html:' + cache_id))


	# Detect the edit verb
	if url_verb == 'edit':
		# Enforce authorizations (FIXME: SHOW A REAL ERROR!)
		if not have_edit:
			raise ESPError(False), "You don't have permission to edit this page."

		m = ESPMarkdown(qsd_rec.content, media={})

		m.toString()
#		assert False, m.BrokenLinks()
		
		# Render an edit form
		return render_to_response('qsd_edit.html', request, (branch, section), {
			'title'        : qsd_rec.title,
			'content'      : qsd_rec.content,
			'qsdrec'       : qsd_rec,
			'qsd'          : True,
			'missing_files': m.BrokenLinks(),
			'target_url'   : base_url.split("/")[-1] + ".edit.html",
			'return_to_view': base_url.split("/")[-1] + ".html" })

	# Detect the standard read verb
	if url_verb == 'read':		
		if not have_read:
			raise Http404

		#cached_html = cache.get('quasistaticdata_html:' + cache_id)
		#if cached_html == None:
		cached_html = qsd_rec.html()
		#	cache.set('quasistaticdata_html:' + cache_id, cached_html)

		# Render response
		return render_to_response('qsd.html', request, (branch, section), {
			'title': qsd_rec.title,
			'content': cached_html,
			'qsdrec': qsd_rec,
			'have_edit': have_edit,
			'edit_url': base_url + ".edit.html" })
	
	# Operation Complete!
	assert False, 'Unexpected QSD operation'

