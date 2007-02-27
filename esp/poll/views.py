from esp.poll.models import Survey, SurveyResponse, Question, QField, QResponse
from esp.users.models import UserBit
from django.http import Http404
from esp.datatree.models import GetNode
from esp.users.models import GetNodeOrNoBits
from esp.web.views.navBar import makeNavBar
from esp.web.util.main import navbar_data, preload_images, render_to_response

# Create your views here.

def poll(request, branch, url_name, url_verb, base_url):
    # Display a poll.
    # Should have a UI that's very similar to displaying a QSD page.
    #
    # (aseering 12/9/2006: Note that the source from this function
    # was originally copy&pasted from the source to the qsd renderer,
    # though it has been extensively modified

    # Detect edit authorizations
    have_edit = UserBit.UserHasPerms( request.user, branch, GetNode('V/Administer/Edit') )
    have_read = UserBit.UserHasPerms( request.user, branch, GetNode('V/Flags/Public') )
    
    # Fetch the QSD object
    poll_recs = Survey.objects.filter( path = branch, name = url_name ).order_by('-create_date')
    if poll_recs.count() < 1:
        assert False, "No such poll exists, and we haven't written an editor yet"
    poll_rec = poll_recs[0]
        
    #if url_verb == 'create':
    #    poll_rec.save()
    #    url_verb = 'edit'
        
    # Detect POST
    if request.POST.has_key('post_edit'):
        # Enforce authorizations (FIXME: SHOW A REAL ERROR!)
        if not have_edit:
            return HttpResponseNotAllowed(['GET'])
        
        poll_rec_new = Survey()
        poll_rec_new.path = branch
        poll_rec_new.name = url_name
        poll_rec_new.author = request.user
        poll_rec_new.title = request.POST['title']
        poll_rec_new.save()
        poll_rec = poll_rec_new

    # Detect the edit verb
    if url_verb == 'edit':
        # Enforce authorizations (FIXME: SHOW A REAL ERROR!)
        if not have_edit:
            assert False, 'Insufficient permissions for QSD edit'
            raise Http404

        assert False, "We don't know how to edit yet!"
        
		# Render an edit form
		#return render_to_response('qsd_edit.html', request, None, {
		#	'title': qsd_rec.title,
		#	'content': qsd_rec.content,
		#	'qsdrec': qsd_rec,
		#	'missing_files': m.BrokenLinks(),
		#	'target_url': base_url.split("/")[-1] + ".edit.html",
		#	'return_to_view': base_url.split("/")[-1] + ".html" })

    # Detect the standard read verb
    if url_verb == 'read':		
        if not have_read:
            assert False, 'Insufficient permissions for QSD read'
            raise Http404

        # Render response
        return render_to_response('poll.html', request, branch, {
            'title': poll_rec.title,
            'content': poll_rec.html(),
            'qsdrec': poll_rec,
            'have_edit': have_edit,
            'edit_url': base_url + ".edit.html" })

    # jalonso: Operation Complete!
    # aseering: Uh..  Sure...  If you say so
    assert False, 'Unexpected QSD operation'
    raise Http404
