# -*- coding: utf-8 -*-
import datetime
from south.v2 import SchemaMigration
import reversion
from reversion.management.commands import createinitialrevisions
from south.db import db
from django.db import models
from esp.qsd.models import QuasiStaticData
from esp.users.models import ESPUser
from esp.web.models import NavBarCategory
from reversion.models import Version, ContentType

class Migration(SchemaMigration):

	def forwards(self, orm):
		print "Running reversion.management.commands.createinitialrevisions (this could take several minutes)..."
		app = models.get_app('qsd')
		model_class = models.get_model('qsd', 'QuasiStaticData')
		createinitialrevisions_command = createinitialrevisions.Command()
		createinitialrevisions_command.create_initial_revisions(app, model_class, "QSD initial revisions.", 500)
		print "Finished running reversion.management.commands.createinitialrevisions."

		print "Creating initial revisions for QSD objects (this may take a while)..."

		# go through list of QuasiStaticData ordered by URL and
		#  create a new object for each group with the same URL
		# (and delete old objects)
		qsdObjects = QuasiStaticData.objects.order_by('url', 'create_date')
		lastQsd = None
		counter = 0

		for qsd in qsdObjects:
			if lastQsd and lastQsd.url == qsd.url:
				try:
					with reversion.create_revision():
						lastQsd.author = qsd.author
						lastQsd.content = qsd.content
						lastQsd.title = qsd.title
						lastQsd.description = qsd.description
						lastQsd.nav_category = qsd.nav_category
						lastQsd.keywords = qsd.keywords
						lastQsd.disabled = qsd.disabled
						lastQsd.create_date = qsd.create_date

						if lastQsd.disabled is None:
							lastQsd.disabled = False

						lastQsd.save()
				except (ESPUser.DoesNotExist, NavBarCategory.DoesNotExist):
					print "... Warning: skipping " + str(qsd.url) + "/" + str(qsd.id) + " due to DoesNotExist error"
			else:
				with reversion.create_revision():
					lastQsd = qsd.copy()

					if lastQsd.disabled is None:
						lastQsd.disabled = False

					lastQsd.save()

			# here we want to delete both the QSD objects itself
			#  but also any revisions that we already have filed for it
			qsdRevisions = reversion.get_for_object(qsd)
			qsd.delete()

			for qsdRevision in qsdRevisions:
				qsdRevision.delete()

			counter += 1
			if counter % 1000 == 0:
				print "... " + str(counter) + "/" + str(len(qsdObjects))

		print "Finished creating initial revisions for QSD objects."
		print "Updating dates for newly created revisions"

		for version in Version.objects.filter(content_type=ContentType.objects.get_for_model(QuasiStaticData)):
			revision = version.revision
			revision.date_created = version.field_dict['create_date']
			revision.save()

		print "Finished updating revision dates."

	def backwards(self, orm):
		print "Converting from reversion format to separate-QSD format (this may take a while)..."

		# go through each QuasiStaticData, get reversions, and create new objects for each reversion
		# then delete the object

		qsdObjects = QuasiStaticData.objects.all()
		counter = 0

		for qsd in qsdObjects:
			# reversion.get_for_object will return in descending order by create date
			# but we want to create these objects in the reverse order

			for qsdRevision in reversed(reversion.get_for_object(qsd)):
				if all (k in qsdRevision.field_dict for k in ('url', 'author', 'content', 'title', 'description', 'nav_category', 'keywords', 'disabled', 'create_date')):
					qsdCopy = QuasiStaticData()
					qsdCopy.url = qsdRevision.field_dict['url']
					qsdCopy.author = ESPUser.objects.get(id=qsdRevision.field_dict['author'])
					qsdCopy.content = qsdRevision.field_dict['content']
					qsdCopy.title = qsdRevision.field_dict['title']
					qsdCopy.description = qsdRevision.field_dict['description']
					qsdCopy.nav_category = NavBarCategory.objects.get(id=qsdRevision.field_dict['nav_category'])
					qsdCopy.keywords = qsdRevision.field_dict['keywords']
					qsdCopy.disabled = qsdRevision.field_dict['disabled']
					qsdCopy.create_date = qsdRevision.revision.date_created
					qsdCopy.save()

			qsd.delete()

			counter += 1
			if counter % 50 == 0:
				print "... " + str(counter) + "/" + str(len(qsdObjects))

		print "Finished QSD conversion"

	models = {
		'auth.group': {
			'Meta': {'object_name': 'Group'},
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
			'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
		},
		'auth.permission': {
			'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
			'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
			'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
		},
		'auth.user': {
			'Meta': {'object_name': 'User'},
			'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
			'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
			'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
			'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
			'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
			'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
			'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
			'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
			'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
			'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
			'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
		},
		'contenttypes.contenttype': {
			'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
			'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
			'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
		},
		'datatree.datatree': {
			'Meta': {'unique_together': "(('name', 'parent'),)", 'object_name': 'DataTree'},
			'friendly_name': ('django.db.models.fields.TextField', [], {}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'lock_table': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
			'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
			'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'child_set'", 'null': 'True', 'to': "orm['datatree.DataTree']"}),
			'range_correct': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
			'rangeend': ('django.db.models.fields.IntegerField', [], {}),
			'rangestart': ('django.db.models.fields.IntegerField', [], {}),
			'uri': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
			'uri_correct': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
		},
		'qsd.espquotations': {
			'Meta': {'object_name': 'ESPQuotations'},
			'author': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
			'content': ('django.db.models.fields.TextField', [], {}),
			'create_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 9, 18, 0, 0)'}),
			'display': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
		},
		'qsd.quasistaticdata': {
			'Meta': {'object_name': 'QuasiStaticData'},
			'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
			'content': ('django.db.models.fields.TextField', [], {}),
			'create_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
			'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
			'disabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'keywords': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
			'name': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
			'nav_category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['web.NavBarCategory']"}),
			'title': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
			'url': ('django.db.models.fields.CharField', [], {'max_length': '256'})
		},
		'web.navbarcategory': {
			'Meta': {'object_name': 'NavBarCategory'},
			'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']", 'null': 'True', 'blank': 'True'}),
			'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
			'include_auto_links': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
			'long_explanation': ('django.db.models.fields.TextField', [], {}),
			'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
			'path': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '64'})
		}
	}

	complete_apps = ['qsd']
