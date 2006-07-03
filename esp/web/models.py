from django.db import models
from esp.watchlists.models import Datatree, GetNode
from esp.lib.markdown import markdown

# Create your models here.

class QuasiStaticData(models.Model):
	""" A Markdown-encoded web page """
	path = models.ForeignKey(Datatree)
	content = models.TextField()
	name = models.SlugField()

	def __str__(self):
		return ( '/'.join(self.path.tree_encode())  + ':' + self.name + '.html' )

	class Admin:
		pass

	def html(self):
		return markdown(self.content)

	@staticmethod
	def find_by_url_parts(parts):
		""" Fetch a QSD record by its url parts """
		# Get the Q_Web root
		Q_Web = GetNode('Q/Web')

		# Extract the last part
		filename = parts.pop()

		# Find the branch
		branch = Q_Web.tree_decode( parts )

		# Find the record
		qsd = QuasiStaticData.objects.filter( path = branch, name = filename )

		# Operation Complete!
		return qsd[0]
