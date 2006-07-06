from django.db import models
from esp.datatree.models import DataTree, GetNode
from esp.lib.markdown import markdown
from esp.users.models import UserBit

# Create your models here.

class Entry(models.Model):
	""" A Markdown-encoded miniblog entry """
	anchor = models.ForeignKey(DataTree)
	title = models.CharField(maxlength=256)
	timestamp = models.DateTimeField(auto_now=True)
	content = models.TextField()

	def __str__(self):
		return ( self.anchor.full_name() + ' (' + str(self.timestamp) + ')' )
	
	def html(self):
		return markdown(self.content)
	
	@staticmethod
	def find_posts_by_perms(self, user, verb):
		""" Fetch a list of relevant posts for a given user and verb """
		# Get the QuerySet for the specified user and verb
		q_list = [ x.qsc for x in UserBit.bits_get_qsc( user, verb ) ]

		# FIXME: This code should be compressed into a single DB query
		# ...using the extra() QuerySet method.

		# Extract entries associated with a particular branch
		res = []
		for q in q_list:
			for entry in Entry.objects.filter(anchor__rangestart__gte = q.rangestart, anchor__rangestart__lt = q.rangeend):
				res.append( entry )
		
		# Operation Complete!
		return res
	
	class Admin:
		pass
