# django dependencies
from django.db import models

# esp dependencies
from esp.db.fields import AjaxForeignKey
from esp.users.models import ESPUser

MAX_DEPTH = 5

class UserForwarder(models.Model):
    """
    Links source user to target user, to make all login sessions under target.

    """
    source = AjaxForeignKey(ESPUser, related_name='forwarders_out', unique=True)
    target = AjaxForeignKey(ESPUser, related_name='forwarders_in')

    # Django tries to figure out the correct app label by going one level up.
    # Since we've had to shard users.models, this isn't quite enough.
    # So we need to specify this explicitly.
    class Meta:
        app_label = 'users'

    def updateTarget(self, target, flatten = True, save = True):
        """
        Updates target, avoiding circularity.

        Sets self.target to:
            if target never forwards to self.source:
                the user to which target ultimately forwards
            else (if target forwards to self.source):
                target, as given

        If save is set, saves self. You basically always want this set.

        If flatten is set, rewrites intervening forwarders to point directly
        to the actual target. This includes those pointing to self.source.
        This has no effect if save is not set.

        Assuming no circularity initially, preserves absence of circularity.
        Vulnerable to race conditions.
        May hit the database a lot if MAX_DEPTH is large.

        """
        # Prepare rewrites
        rewrites = []
        deletes = []
        if not save:
            flatten = False
        if flatten:
            rewrites.extend(self.source.forwarders_in.all())
        # Find the real target
        original_target = target
        for i in xrange(MAX_DEPTH):
            # Get the next forwarder if it exists
            if target.forwarders_out.count() == 0:
                break
            f = target.forwarders_out.get()
            # Check for circular references
            if f.target == self.source:
                target = original_target
                break
            # Follow to the next user
            rewrites.append(f) # Don't bother checking flatten -- do it later
            target = f.target
        # Update
        self.target = target
        if save:
            self.save()
            # Flatten
            if flatten:
                for f in rewrites:
                    f.target = target
                    if f.source == f.target:
                        f.delete()
                    else:
                        f.save()

    @staticmethod
    def forward(source, target):
        """Forward from source to target, creating a forwarder if needed."""
        if source.forwarders_out.count() > 0:
            f = source.forwarders_out.get()
        else:
            f = UserForwarder()
            f.source = source
        f.updateTarget(target)

    @staticmethod
    def follow(user):
        """
        Follow any forwarder from user.

        Returns (new user, True if forwarded).

        Remark: We don't handle chained forwarders. That's done at write time
        (with forward() or updateTarget()), to save computation.

        """
        if user.forwarders_out.count() > 0:
            ans = user.forwarders_out.get().target
            for extra in ['backend']:
                if hasattr(user, extra):
                    ans.__dict__[extra] = user.__dict__[extra]
            return (ans, True)
        else:
            return (user, False)

    def __unicode__(self):
        return u'%s to %s' % (unicode(self.source), unicode(self.target))
