# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

import collections


def canonicalize_names(all_resources):
    """Do some basic combining of resources with similar names.

    Returns a dict of name -> set of resources that should be represented
    by it.  Not intended to be super-smart, just do some basic combining of
    obvious things.
    """
    canonical_names = collections.defaultdict(set)
    for res in all_resources:
        canonical_names[res.name].add(res)
    for name in canonical_names.keys():
        new_name = None
        if ' ' in name:
            with_dashes = name.replace(' ', '-')
            without_spaces = name.replace(' ', '')
            if with_dashes in canonical_names:
                new_name = with_dashes
            elif without_spaces in canonical_names:
                new_name = without_spaces
        if new_name:
            canonical_names[new_name] |= canonical_names[name]
            del canonical_names[name]
    return canonical_names


def populate_locations(apps, schema_editor):
    Location = apps.get_model("resources", "Location")
    Resource = apps.get_model("resources", "Resource")
    ClassSection = apps.get_model("program", "ClassSection")

    all_resources = Resource.objects.filter(res_type__name='Classroom')
    canonical_names = canonicalize_names(all_resources)
    for name, resources in canonical_names.iteritems():
        # Take the newest (highest id) capacity as correct, and create the
        # resource
        new_cap = sorted(list(resources), key=lambda r: -r.id)[0].num_students
        location = Location(name=name, capacity=new_cap)
        location.save()
        for resource in resources:
            # mark it as the location corresponding to the old resource
            # groups.  don't delete the resources for now, we'll do that
            # in a separate migration.
            resource.res_group.location = location
            resource.res_group.save()

            resource.event.available_locations.add(location)

            scheduled_sections = ClassSection.objects.filter(
                resourceassignment__resource=resource)
            # Not sure why there would be more than one section scheduled
            # in one Resource, but just in case...
            for section in scheduled_sections:
                section.locations.add(location)


def clear_locations(apps, schema_editor):
    Location = apps.get_model("resources", "Location")
    Location.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0003_auto_20151017_2134'),
        ('program', '0003_classsection_locations'),
    ]

    operations = [
        migrations.RunPython(populate_locations, clear_locations)
    ]
