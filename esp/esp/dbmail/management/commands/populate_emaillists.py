"""
Management command to populate default EmailList entries.

This command creates the default EmailList entries that are needed for
email routing to work properly. It's useful for:
- New site installations
- Sites that were created before the default email lists were added
- Recovering from accidental deletion of email lists

Usage:
    python manage.py populate_emaillists
    python manage.py populate_emaillists --force  # Recreate even if lists exist
"""

from django.core.management.base import BaseCommand
from esp.dbmail.models import EmailList


class Command(BaseCommand):
    help = 'Populate default EmailList entries for email routing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of default email lists even if they already exist',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        # Check if email lists already exist
        existing_count = EmailList.objects.count()
        
        if existing_count > 0 and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'EmailList table already contains {existing_count} entries. '
                    'Use --force to recreate default lists.'
                )
            )
            return
        
        if force and existing_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Removing {existing_count} existing EmailList entries...'
                )
            )
            EmailList.objects.all().delete()
        
        # Define default email lists
        default_lists = [
            {
                'regex': r'^([a-zA-Z0-9_]+)s([0-9]+)c([0-9]+)-(students|teachers|class)$',
                'seq': 10,
                'handler': 'SectionList',
                'description': 'Section mailing lists (e.g., S123C1-students)',
                'admin_hold': False,
                'cc_all': False,
            },
            {
                'regex': r'^([a-zA-Z0-9_]+)s([0-9]+)-(students|teachers|class)$',
                'seq': 20,
                'handler': 'ClassList',
                'description': 'Class mailing lists (e.g., S123-students)',
                'admin_hold': False,
                'cc_all': False,
            },
            {
                'regex': r'^([a-zA-Z0-9_\.\-]+)$',
                'seq': 30,
                'handler': 'PlainList',
                'description': 'Plain redirect lists (looks up in PlainRedirect table)',
                'admin_hold': False,
                'cc_all': False,
            },
            {
                'regex': r'^([a-zA-Z0-9_\.\-]+)$',
                'seq': 40,
                'handler': 'UserEmail',
                'description': 'User email forwarding (forwards to user\'s email address)',
                'admin_hold': False,
                'cc_all': False,
            },
        ]
        
        # Create the email lists
        created_count = 0
        for list_data in default_lists:
            email_list = EmailList.objects.create(**list_data)
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created EmailList: {email_list.description} '
                    f'(seq={email_list.seq}, handler={email_list.handler})'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully created {created_count} default EmailList entries.'
            )
        )
        self.stdout.write(
            'Email routing should now work properly. '
            'You can view and manage these lists at /admin/dbmail/emaillist/'
        )
