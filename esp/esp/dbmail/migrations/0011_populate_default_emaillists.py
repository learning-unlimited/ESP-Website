# -*- coding: utf-8 -*-
# Generated migration to populate default EmailList entries for new sites

from django.db import migrations


def create_default_emaillists(apps, schema_editor):
    """
    Create default EmailList entries that should exist for all sites.
    These handle common email routing patterns like class lists, section lists,
    user emails, and plain redirects.
    """
    EmailList = apps.get_model('dbmail', 'EmailList')
    
    # Only create defaults if no EmailList entries exist
    # (to avoid duplicating on existing sites)
    if EmailList.objects.exists():
        return
    
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
    
    for list_data in default_lists:
        EmailList.objects.create(**list_data)


def remove_default_emaillists(apps, schema_editor):
    """
    Reverse migration: remove the default EmailList entries.
    Only removes entries that match our default patterns exactly.
    """
    EmailList = apps.get_model('dbmail', 'EmailList')
    
    # Remove only the default entries we created
    default_regexes = [
        r'^([a-zA-Z0-9_]+)s([0-9]+)c([0-9]+)-(students|teachers|class)$',
        r'^([a-zA-Z0-9_]+)s([0-9]+)-(students|teachers|class)$',
        r'^([a-zA-Z0-9_\.\-]+)$',
    ]
    
    for regex in default_regexes:
        EmailList.objects.filter(regex=regex).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dbmail', '0010_textofemail_messagerequest'),
    ]

    operations = [
        migrations.RunPython(create_default_emaillists, remove_default_emaillists),
    ]
