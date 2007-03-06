from django.db import models
from esp.datatree.models import DataTree, GetNode
from esp.lib.markdown import markdown
from django.contrib.auth.models import User
from datetime import datetime

# Create your models here.

class QuasiStaticData(models.Model):
	""" A Markdown-encoded web page """
	path = models.ForeignKey(DataTree)
	name = models.SlugField()
	title = models.CharField(maxlength=256)
	content = models.TextField()

	create_date = models.DateTimeField(default=datetime.now())
	author = models.ForeignKey(User)
	disabled = models.BooleanField(default=False)
	
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


class ESPQuotations(models.Model):
	""" Quotation about ESP """

	content = models.TextField()
	display = models.BooleanField()
	author  = models.CharField(maxlength=64)
	create_date = models.DateTimeField(default=datetime.now())

	@staticmethod
	def getQuotation():
		import random
		cutoff = .9
		if random.random() > cutoff:
			return None
		return ESPQuotations.objects.filter(display=True).order_by('?')[0]
		

	class Admin:
		pass
