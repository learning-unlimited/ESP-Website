# Create your views here.

from blog.myblog.models import BlogEntry
from django.shortcuts import render_to_response
from django.http import Http404

def list_blogs(request):
	entries = BlogEntry.objects.all()
	return render_to_response('blog_list.html', { 'entries': entries })
