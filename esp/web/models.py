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
	def find_by_url_parts(parts):
		""" Fetch a QSD record by its url parts """
		# Get the Q_Web root
		Q_Web = GetNode('Q/Web')

		# Extract the last part
		filename = parts.pop()

		# Find the branch
		try:
			branch = Q_Web.tree_decode( parts )
		except DataTree.NoSuchNodeException:
			raise QuasiStaticData.DoesNotExist

		# Find the record
		qsd = QuasiStaticData.objects.filter( path = branch, name = filename )
		if len(qsd) < 1:
			raise QuasiStaticData.DoesNotExist

		# Operation Complete!
		return qsd[0]

class NavBarEntry(models.Model):
	""" An entry for the secondary navigation bar """
	path = models.ForeignKey(DataTree)
	sort_rank = models.IntegerField()
	link = models.CharField(maxlength=256)
	text = models.CharField(maxlength=64)
	indent = models.BooleanField()

	def __str__(self):
		return ( self.path.full_name() + ':' + str(self.sort_rank) + ' (' + self.text + ')'  )
	
	class Admin:
		pass
	
	@staticmethod
	def find_by_url_parts(parts):
		""" Fetch a QuerySet of NavBarEntry objects by the url parts """
		# Get the Q_Web root
		Q_Web = GetNode('Q/Web')

		# Remove the last component
		parts.pop()

		# Find the branch
		try:
			branch = Q_Web.tree_decode( parts )
		except DataTree.NoSuchNodeException, ex:
			branch = ex.anchor
		if branch is None:
			raise NavBarEntry.DoesNotExist
		
		# Find the valid entries
		return NavBarEntry.objects.filter(path__rangestart__lte=branch.rangestart,path__rangeend__gte=branch.rangeend).order_by('sort_rank')
