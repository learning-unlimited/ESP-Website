# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AJAXChangeLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='AJAXChangeLogEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('index', models.IntegerField()),
                ('timeslots', models.CharField(max_length=256)),
                ('room_name', models.CharField(max_length=256)),
                ('cls_id', models.IntegerField()),
                ('time', models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name='ClassRegModuleInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('allow_coteach', models.BooleanField(default=True, help_text=b'Check this box to allow teachers to specify co-teachers.')),
                ('set_prereqs', models.BooleanField(default=True, help_text=b'Check this box to allow teachers to enter prerequisites for each class that are displayed separately on the catalog.')),
                ('class_max_duration', models.IntegerField(help_text=b'The maximum length of a class, in minutes.', null=True, blank=True)),
                ('class_min_cap', models.IntegerField(help_text=b'The minimum number of students a teacher can choose as their class capacity.', null=True, blank=True)),
                ('class_max_size', models.IntegerField(help_text=b'The maximum number of students a teacher can choose as their class capacity.', null=True, blank=True)),
                ('class_size_step', models.IntegerField(help_text=b'The interval for class capacity choices.', null=True, blank=True)),
                ('class_other_sizes', models.CommaSeparatedIntegerField(help_text=b"Force the addition of these options to teachers' choices of class size.  (Enter a comma-separated list of integers.)", max_length=100, null=True, blank=True)),
                ('allowed_sections', models.CommaSeparatedIntegerField(help_text=b'Allow this many independent sections of a class (comma separated list of integers). Leave blank to allow arbitrarily many.', max_length=100, blank=True)),
                ('session_counts', models.CommaSeparatedIntegerField(help_text=b'Possibilities for the number of days that a class could meet (comma separated list of integers). Leave blank if this is not a relevant choice for the teachers.', max_length=100, blank=True)),
                ('num_teacher_questions', models.PositiveIntegerField(default=1, help_text=b'The maximum number of application questions that can be specified for each class.', null=True, blank=True)),
                ('color_code', models.CharField(max_length=6, null=True, blank=True)),
                ('allow_lateness', models.BooleanField(default=False)),
                ('ask_for_room', models.BooleanField(default=True, help_text=b'If true, teachers will be asked if they have a particular classroom in mind.')),
                ('use_class_size_max', models.BooleanField(default=True)),
                ('use_class_size_optimal', models.BooleanField(default=False)),
                ('use_optimal_class_size_range', models.BooleanField(default=False)),
                ('use_allowable_class_size_ranges', models.BooleanField(default=False)),
                ('open_class_registration', models.BooleanField(default=False, help_text=b'If true, teachers will be presented with an option to register for an "open class".')),
                ('progress_mode', models.IntegerField(default=1, help_text=b'Select which to use on teacher reg: 1=checkboxes, 2=progress bar, 0=neither.')),
            ],
        ),
        migrations.CreateModel(
            name='DBReceipt',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('action', models.CharField(default=b'confirm', max_length=80)),
                ('receipt', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='ProgramModuleObj',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('seq', models.IntegerField()),
                ('required', models.BooleanField(default=False)),
                ('required_label', models.CharField(max_length=80, null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='StudentClassRegModuleInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('enforce_max', models.BooleanField(default=True, help_text=b'Check this box to prevent students from signing up for full classes.')),
                ('class_cap_multiplier', models.DecimalField(default=b'1.00', help_text=b'A multiplier for class capacities (set to 0.5 to cap all classes at half their stored capacity).', max_digits=3, decimal_places=2)),
                ('class_cap_offset', models.IntegerField(default=0, help_text=b'Offset for class capacities (this number is added to the original capacity of every class).')),
                ('apply_multiplier_to_room_cap', models.BooleanField(default=False, help_text=b'Apply class cap multipler and offset to room capacity instead of class capacity.')),
                ('use_priority', models.BooleanField(default=False, help_text=b'Check this box to enable priority registration.')),
                ('priority_limit', models.IntegerField(default=3, help_text=b'The maximum number of choices a student can make per timeslot when priority registration is enabled.')),
                ('use_grade_range_exceptions', models.BooleanField(default=False, help_text=b'Check this box to enable grade range exceptions.')),
                ('register_from_catalog', models.BooleanField(default=False, help_text=b'Check this box to allow students to add classes from the catalog page if they are logged in.')),
                ('visible_enrollments', models.BooleanField(default=True, help_text=b'Uncheck this box to prevent students from seeing enrollments on the catalog.')),
                ('visible_meeting_times', models.BooleanField(default=True, help_text=b"Uncheck this box to prevent students from seeing classes' meeting times on the catalog.")),
                ('confirm_button_text', models.CharField(default=b'Confirm', help_text=b'Label for the "confirm" button at the bottom of student reg.', max_length=80)),
                ('view_button_text', models.CharField(default=b'View Receipt', help_text=b'Label for the "get receipt" button (for already confirmed students) at the bottom of student reg.', max_length=80)),
                ('cancel_button_text', models.CharField(default=b'Cancel Registration', help_text=b'Label for the "cancel" button at the bottom of student reg.', max_length=80)),
                ('temporarily_full_text', models.CharField(default=b'Class temporarily full; please check back later', help_text=b'The text that replaces the "Add class" button when the class has reached its adjusted capacity', max_length=255)),
                ('cancel_button_dereg', models.BooleanField(default=False, help_text=b'Check this box to remove a student from all of their classes when they cancel their registration.')),
                ('progress_mode', models.IntegerField(default=1, help_text=b'Select which to use on student reg: 1=checkboxes, 2=progress bar, 0=neither.')),
                ('send_confirmation', models.BooleanField(default=False, help_text=b'Check this box to send each student an email the first time they confirm their registration.  You must define an associated DBReceipt of type "confirmemail".')),
                ('show_emailcodes', models.BooleanField(default=True, help_text=b'Uncheck this box to prevent email codes (i.e. E534, H243) from showing up on catalog and fillslot pages.')),
                ('force_show_required_modules', models.BooleanField(default=True, help_text=b'Check this box to require that users see and fill out "required" modules before they can see the main StudentReg page')),
                ('module', models.ForeignKey(editable=False, to='modules.ProgramModuleObj')),
            ],
        ),
    ]
