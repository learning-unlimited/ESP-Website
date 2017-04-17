""" Overridden version of createsuperuser """

from django.contrib.auth.management.commands.createsuperuser \
    import Command as BaseSuperUserCommand

from esp.users.models import ESPUser

class Command(BaseSuperUserCommand):
    def handle(self, *args, **options):
        print "HELLO!"
        super(Command, self).handle(*args, **options)

        # All superusers should be members of the group "Administrator". We
        # don't have the name of the one that was just created, so apply this
        # action to all superusers in the database.
        superusers = ESPUser.objects.filter(is_superuser=True)
        for user in superusers:
            user.makeRole("Administrator")
        print "GOODBYE!"
