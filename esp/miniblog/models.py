from django.db import models
from esp.datatree.models import DataTree, GetNode
from esp.lib.markdown import markdown
from esp.users.models import UserBit
from esp.dbmail.models import MessageRequest
from django.contrib.auth.models import User

# Create your models here.

class Entry(models.Model):
	""" A Markdown-encoded miniblog entry """
	anchor = models.ForeignKey(DataTree)
	title = models.CharField(maxlength=256) # Plaintext; shouldn't contain HTML, for security reasons, though HTML will probably be passed through intact
	timestamp = models.DateTimeField(auto_now=True)
	content = models.TextField() # Markdown-encoded
	sent    = models.BooleanField()
	email   = models.BooleanField()
	fromuser = models.ForeignKey(User, blank=True, null=True)
	priority = models.IntegerField(blank=True, null=True) # Message priority (role of this field not yet well-defined -- aseering 8-10-2006)

	def __str__(self):
		return ( self.anchor.full_name() + ' (' + str(self.timestamp) + ')' )

	def html(self):
		return markdown(self.content)

	def makeTitle(self):
		return self.title

	def makeUrl(self):
		return "/blog/"+str(self.id)+"/"
	
	@staticmethod
	def find_posts_by_perms(user, verb, qsc=None):
		""" Fetch a list of relevant posts for a given user and verb """
		if qsc==None:
			return UserBit.find_by_anchor_perms(Entry,user,verb)
		else:
			return UserBit.find_by_anchor_perms(Entry,user,verb,qsc=qsc)
	class Admin:
		pass
	
	@staticmethod
	def post( user_from, anchor, subject, content, email=False):
		newentry = Entry()
		newentry.content = content
		newentry.title = subject
		newentry.anchor = anchor
		newentry.email  = email
		newentry.sent  = False
		newentry.fromuser = user_from

		newentry.save()

