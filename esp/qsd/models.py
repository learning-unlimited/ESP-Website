from django.db import models
from esp.datatree.models import DataTree, GetNode
from esp.lib.markdown import markdown

# Create your models here.

class QuasiStaticData(models.Model):
	""" A Markdown-encoded web page """
	path = models.ForeignKey(DataTree)
	name = models.SlugField()
	title = models.CharField(maxlength=256)
	content = models.TextField()

	def __str__(self):
		return ( self.path.full_name() + ':' + self.name + '.html' )

	class Admin:
		pass

	def html(self):
		return markdown(self.content)

	@staticmethod
	def find_by_url_parts(base, parts):
		""" Fetch a QSD record by its url parts """
		# Extract the last part
		filename = parts.pop()

		# Find the branch
		try:
			branch = base.tree_decode( parts )
		except DataTree.NoSuchNodeException:
			raise QuasiStaticData.DoesNotExist

		# Find the record
		qsd = QuasiStaticData.objects.filter( path = branch, name = filename )
		if len(qsd) < 1:
			raise QuasiStaticData.DoesNotExist

		# Operation Complete!
		return qsd[0]

