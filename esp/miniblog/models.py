from django.db import models
from esp.datatree.models import DataTree, GetNode
from esp.lib.markdown import markdown

# Create your models here.

class Entry(models.Model):
	""" A Markdown-encoded miniblog entry """
	anchor = models.ForeignKey(DataTree)
	timestamp = models.DateTimeField(auto_now=True)
	content = models.TextField()

	def __str__(self):
		return ( self.anchor.full_name() + ' (' + self.timestamp + ')' )
	
	def html(self):
		return markdown(self.content)
