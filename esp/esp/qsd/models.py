from __future__ import absolute_import
from __future__ import unicode_literals
from django.utils.encoding import python_2_unicode_compatible
from six.moves import map
import six
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""
from datetime import datetime
import hashlib

from django.db import models, transaction
from django.db.utils import IntegrityError

from markdown import markdown
from reversion import revisions as reversion
from esp.db.fields import AjaxForeignKey
from argcache import cache_function
from esp.web.models import NavBarCategory, default_navbarcategory
from esp.users.models import ESPUser


class QSDConflict(Exception):
    """
    Raised by QSDManager.save_with_conflict_check() when the QSD at a url was
    created, deleted, or changed by someone else since the editor started
    editing it.

    `current` is the row now at that url (or None if it's gone). `history`
    lists the intervening edits (most recent first) as
    [{'user': ..., 'date': ...}, ...].
    """
    def __init__(self, current, history):
        self.current = current
        self.history = history
        super(QSDConflict, self).__init__(
            'The QSD at this url changed since editing started.')


def edit_history(obj, since_version_id=None, limit=5):
    """
    Returns the most recent edits to obj, as
    [{'version_id': ..., 'user': ..., 'date': ...}, ...], most recent first.
    If since_version_id is given, only includes versions strictly newer than
    it (i.e. the edits the current editor hasn't seen). If limit is None,
    returns the full history instead of just the most recent few.

    Uses the QuasiStaticData snapshot's own author/create_date fields, not
    reversion's Revision.user/date_created -- this project never calls
    reversion.set_user() (no RevisionMiddleware either), so Revision.user is
    always None regardless of who actually made the edit.
    """
    if obj is None or obj.pk is None:
        return []
    history = []
    for version in reversion.get_for_object(obj):
        if since_version_id is not None and version.pk <= since_version_id:
            break
        snapshot = version.object_version.object
        history.append({'version_id': version.pk, 'user': snapshot.author, 'date': snapshot.create_date})
        if limit is not None and len(history) >= limit:
            break
    return history


def version_snapshot(obj, version_id):
    """
    Returns the QuasiStaticData snapshot stored in one of obj's own past
    versions (identified by reversion Version pk), or None if version_id
    doesn't belong to obj's history -- e.g. a stale revert link from before
    the row was deleted and recreated (a new pk starts a new version
    lineage), or a forged id. Deliberately scoped to obj's own history
    rather than a bare Version.objects.get(pk=...), so a revert can only
    ever restore content that really was this row's content at some point.
    """
    if obj is None or obj.pk is None:
        return None
    for version in reversion.get_for_object(obj):
        if version.pk == version_id:
            return version.object_version.object
    return None


def strip_default_content_indentation(content):
    """
    Strips unintended leading whitespace from default/fallback QSD content
    (used both by get_by_url_else_init, when constructing a brand new row,
    and by templatetags/render_qsd.py's InlineQSDNode, when exposing that
    same default for an existing row's "load the default content" option).

    Because of the way templates are usually written, there will often be
    unintended whitespace at the beginnings of lines of the default content
    of an inline QSD. Usually a line starts with some template indentation
    before the actual content. However, Markdown will interpret this as a
    code block. To avoid this, we assume that the default content will
    never purposely use Markdown code blocks, and we strip this unintended
    space.
    """
    content = six.text_type(content.lstrip())
    content = content.split('\n')
    content = list(map(six.text_type.lstrip, content))
    return '\n'.join(content)


def _is_stale(current, orig_id, orig_version):
    """
    True if `current` (the row now at some url, or None if there isn't one)
    no longer matches what an editor started from (orig_id/orig_version).
    """
    if orig_id is None:
        return current is not None
    return (current is None or current.pk != orig_id
            or current.latest_version_id() != orig_version)


def _history_for_conflict(current, orig_id, orig_version):
    """
    The edit history to show for a conflict against (orig_id, orig_version):
    just the edits since orig_version if `current` is still the same row
    (content changed under us), or the full history if the row was created
    fresh or deleted-and-recreated (there's no earlier point of ours to
    diff against).
    """
    if orig_id is not None and current is not None and current.pk == orig_id:
        return edit_history(current, since_version_id=orig_version)
    return edit_history(current)


class QSDManager(models.Manager):

    def check_freshness(self, url, orig_id, orig_version):
        """
        Non-destructive freshness check: does not lock or mutate anything,
        so it's safe to call before an editor starts typing, to warn them
        their starting point is already out of date. This is advisory only
        -- save_with_conflict_check is the atomic, authoritative guard used
        at actual save time.

        Returns (stale, history).
        """
        current = self.get_by_url(url)
        if not _is_stale(current, orig_id, orig_version):
            return False, []
        return True, _history_for_conflict(current, orig_id, orig_version)

    def save_with_conflict_check(self, url, orig_id, orig_version, populate):
        """
        Atomically verify that the QSD at `url` is still the same row, at the
        same version, that the editor started from -- then apply
        populate(qsd_rec) (a callable that sets fields but does not save) and
        save it.

        orig_id: pk of the row the editor started from, or None if they
        started from a blank page/block (no row existed yet, or it was
        disabled and is being treated as if it didn't exist).
        orig_version: qsd_rec.latest_version_id() as of when the editor
        started, or None if the row had no version yet.

        Raises QSDConflict if the row was created, deleted, or edited by
        someone else in the meantime -- including the case where two requests
        race to create a row at the same (previously nonexistent) url, which
        is caught via the url's uniqueness constraint.
        """
        with transaction.atomic():
            current = self.select_for_update().filter(url=url).first()

            if _is_stale(current, orig_id, orig_version):
                raise QSDConflict(current, _history_for_conflict(current, orig_id, orig_version))

            qsd_rec = current if current is not None else QuasiStaticData(url=url)

            populate(qsd_rec)

            try:
                # Wrap the save in its own revision explicitly, rather than
                # relying on the caller to be wrapped in
                # reversion.create_revision() -- without an active revision,
                # no Version row gets created, latest_version_id() stays
                # None forever, and conflict detection would silently
                # degrade to comparing None != None (i.e. never firing).
                with transaction.atomic(), reversion.create_revision():
                    qsd_rec.save()
            except IntegrityError:
                # Someone else inserted a row at this url between our check
                # above and this save (only possible for the brand-new-page
                # case, since two requests can both pass the "current is
                # None" check before either commits).
                current = self.get_by_url(url)
                raise QSDConflict(current, edit_history(current))

            return qsd_rec

    @cache_function
    def get_by_url(self, url):
        #Besides caching, this also handles finding the latest easily,
        # and returning none when there isn't any such QSD
        #comment from an older version of this function:
        #    aseering 11-15-2009 -- Punt FileDB for this purpose;
        #    it has consistency issues in multi-computer load-balanced setups,
        #    and memcached doesn't have a clear performance disadvantage.
        # Order by id as well as create_date, since multiple rows can share a
        # create_date (e.g. rows created in the same request or by a script),
        # and latest() alone would pick between them arbitrarily.
        return self.filter(url=url).select_related().order_by('-create_date', '-id').first()
    get_by_url.depend_on_row('qsd.QuasiStaticData', lambda qsd: {'url': qsd.url})

    @cache_function
    def get_by_url_else_init(self, url, defaults={}):
        """
        Tries looking up a QSD object by url, using self.get_by_url(). If this
        fails because the url does not have a saved QSD object yet, or the
        latest QSD for the url has been disabled, initializes and returns a
        new QSD object, without saving it to the database.
        """
        qsd_obj = self.get_by_url(url)
        if qsd_obj is None or qsd_obj.disabled:
            qsd_obj = QuasiStaticData(url=url, **defaults)
            qsd_obj.content = strip_default_content_indentation(qsd_obj.content)
        return qsd_obj
    get_by_url_else_init.depend_on_row('qsd.QuasiStaticData', lambda qsd: {'url': qsd.url})

    def __str__(self):
        return "QSDManager()"

    def __repr__(self):
        return "QSDManager()"

def qsd_edit_id(val):
    """ A short hex string summarizing the QSD's URL. """
    return hashlib.sha1(val.encode("UTF-8")).hexdigest()[:8]

@python_2_unicode_compatible
class QuasiStaticData(models.Model):
    """ A Markdown-encoded web page """

    objects = QSDManager()

    url = models.CharField(max_length=256, unique=True, help_text="Full url, without the trailing .html")
    name = models.SlugField(blank=True)
    title = models.CharField(max_length=256)
    content = models.TextField()

    nav_category = models.ForeignKey(NavBarCategory, default=default_navbarcategory)

    create_date = models.DateTimeField(default=datetime.now, editable=False, verbose_name="last edited")
    author = AjaxForeignKey(ESPUser, verbose_name="last modifed by") #I believe that these are,uh, no longer descriptive names. This is silly, but the verbose names should fit better.
    disabled = models.BooleanField(default=False)
    keywords = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def edit_id(self):
        return qsd_edit_id(self.url)

    def latest_version_id(self):
        """
        Returns the pk of the most recent reversion Version for this row, or
        None if it hasn't been saved yet (or was saved outside of a
        reversion-wrapped view, so has no version history). Used as an
        optimistic-concurrency marker: if this doesn't match at save time,
        someone else edited the row in the meantime.
        """
        if self.pk is None:
            return None
        versions = list(reversion.get_for_object(self)[:1])
        return versions[0].pk if versions else None

    def copy(self,):
        """Returns a copy of the current QSD.

        This could be used for versioning QSDs, for example. It will not be
        saved to the DB until .save is called.

        Note that this method maintains the author and created date.
        Client code should probably reset the author to request.user
        and date to datetime.now (possibly with load_cur_user_time)"""
        qsd_new = QuasiStaticData()
        qsd_new.url    = self.url
        qsd_new.author  = self.author
        qsd_new.content = self.content
        qsd_new.title   = self.title
        qsd_new.description  = self.description
        qsd_new.nav_category = self.nav_category
        qsd_new.keywords     = self.keywords
        qsd_new.disabled     = self.disabled
        qsd_new.create_date  = self.create_date
        return qsd_new

    def load_cur_user_time(self, request, ):
        self.author = request.user
        self.create_date = datetime.now()


    def __str__(self):
        return self.url

    @cache_function
    def html(self):
        return markdown(self.content)
    html.depend_on_row('qsd.QuasiStaticData', 'self')

    @staticmethod
    def prog_qsd_url(prog, name):
        """Return the url for a program-qsd with given name

        Will have .html at the end iff name does"""
        parts = name.split(":")
        if len(parts)>1:
            return "/".join([parts[0], prog.url, ":".join(parts[1:])])
        else:
            return "/".join(["programs", prog.url, name])

    @staticmethod
    def program_from_url(url):
        """ If the QSD pertains to a program, figure out which one,
            and return a tuple of the Program object and the QSD name.
            Otherwise return None.  """
        from esp.program.models import Program

        url_parts = url.split('/')
        #   The first part url_parts[0] could be anything, since prog_qsd_url()
        #   takes whatever was specified in the old qsd name
        #   (e.g. 'learn:extrasteps' results in a URL starting with 'learn/',
        #   but you could also have 'foo:extrasteps' etc.)
        #   So, allow any QSD with a program URL in the right place to match.
        if len(url_parts) > 3 and len(url_parts[3]) > 0:
            prog_url = '/'.join(url_parts[1:3])
            progs = Program.objects.filter(url=prog_url)
            if progs.count() == 1:
                if url_parts[0] == 'programs':
                    return (progs[0], '/'.join(url_parts[3:]))
                else:
                    return (progs[0], '%s:' % url_parts[0] + '/'.join(url_parts[3:]))

        return None

    def get_absolute_url(self):
        return "/"+self.url+".html"

    class Meta:
        verbose_name = 'Editable'
