# Create your views here.
from django.template import Context, loader
from demoproj1.polls.models import Poll
from django.http import HttpResponse
from django.http import Http404
from django.shortcuts import render_to_response

def index(request):
        latest_poll_list = Poll.objects.all().order_by('-pub_date')
	t = loader.get_template('polls/index.html')
	c = Context({
		'latest_poll_list': latest_poll_list,
		})
	return HttpResponse(t.render(c))

def detail(request, poll_id):
	p = get_object_or_404(Poll, pk=poll_id)
	return render_to_response('polls/detail.html', {'poll': p})

