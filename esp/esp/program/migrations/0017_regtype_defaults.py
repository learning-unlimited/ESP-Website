# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

def set_my_defaults(apps, schema_editor):
    defaults_dict = {
                        "Enrolled": {"dn": "Enrolled in Class", "des": "Student is currently enrolled in this class"},
                        "Attended": {"dn": "Attended Class", "des": "Student attended this class"},
                        "Accepted": {"dn": "Application Accepted", "des": "Student's application for this class was accepted"},
                        "Request": {"dn": "Class Change Request", "des": "Student made a class change request for this class"},
                        "Interested": {"dn": "Interested in Class", "des": "For old lottery registration, a student would be interested in being placed into this class, but it isn't their first choice"},
                        "SurveyCompleted": {"dn": "Completed Class Survey", "des": "Student filled out the survey for this class"},
                        "Onsite/Webapp": {"dn": "Enrolled Using Webapp", "des": "Student used the onsite webapp to enroll in this class"},
                        "OnSite/ChangedClasses": {"dn": "Enrolled at Onsite", "des": "Student enrolled in this class at onsite registration"},
                        "OnSite/AttendedClass": {"dn": "Enrolled via Attendance", "des": "Student was enrolled in this class because they attended it"},
                    }
    RegistrationType = apps.get_model('program', 'RegistrationType')
    for rt in RegistrationType.objects.all():
        if "Priority/" in rt.name:
            prior_num = int(rt.name.split("Priority/")[1])
            if rt.displayName is None or rt.displayName == u"":
                rt.displayName = "Priority %i" % prior_num
            if rt.description is None or rt.description == u"":
                rt.description = "Student marked this class as their #%i priority in the two-phase class lottery" % prior_num
        if rt.name in defaults_dict.keys():
            if rt.displayName is None or rt.displayName == u"":
                rt.displayName = defaults_dict[rt.name]["dn"]
            if rt.description is None or rt.description == u"":
                rt.description = defaults_dict[rt.name]["des"]
        rt.save()

def reverse_func(apps, schema_editor):
    return

class Migration(migrations.Migration):

    dependencies = [
        ('program', '0016_auto_20200531_1357'),
    ]

    operations = [
        migrations.RunPython(set_my_defaults, reverse_func),
    ]
