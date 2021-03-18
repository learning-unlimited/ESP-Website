from django import forms
from django.forms import widgets
from django.core.validators import RegexValidator
from decimal import Decimal
import datetime

from esp.users.forms import _states

# Lists of all tags used anywhere in the codebase
# Populated by hand, so don't be too surprised if something is missing

# Format:
#   'key': {
#       'is_boolean': is tag used with getBooleanTag? (boolean),
#       'help_text': 'some help text for admins',
#       'default': default value (normally a string or None, but can be a boolean if is_boolean is True or some other type if a custom field is set below),
#       'category': 'category name' (see dictionary at the bottom of this file),
#       'is_setting': show on tag settings page? (boolean),
#       (optional) 'field': a django form field instance (e.g. forms.IntegerField())
#   }

# Any tag used with Tag.getTag()
# or Tag.getBooleanTag() with no program argument
all_global_tags = {
    'teacherreg_custom_forms': {
        'is_boolean': False,
        'help_text': 'JSON list of names of teacher registration custom forms to include in the class registration form',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'allow_global_restypes': {
        'is_boolean': True,
        'help_text': 'Include global resource types in the manage resources and teacher registration options',
        'default': False,
        'category': 'teach',
        'is_setting': True,
    },
    'full_group_name': {
        'is_boolean': False,
        'help_text': 'For places that demand an official-sounding name for the group that goes beyond the INSTITUTION_NAME and ORGANIZATION_SHORT_NAME settings.',
        'default': None,
        'category': 'manage',
        'is_setting': True,
    },
    'nearly_full_threshold': {
        'is_boolean': False,
        'help_text': 'Fraction (as a decimal) of section capacity that determines if a class is \'nearly full\'',
        'default': Decimal(0.75),
        'category': 'teach',
        'is_setting': True,
        'field': forms.DecimalField(min_value=Decimal(0.00), max_value=Decimal(1.00), decimal_places=2),
    },
    'use_class_size_optimal': {
        'is_boolean': True,
        'help_text': 'Should teachers be asked for an optimal class size (instead of maximum size)? Must be set to True for optimal class size options in the class registration module info to have any effect.',
        'default': False,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_difficulty_choices': {
        'is_boolean': False,
        'help_text': 'This controls the choices of the \'Difficulty\' field on the class creation/editing form. This should be a JSON-formatted list of 2-element lists. Example: [[1, "Easy"], [2, "Medium"], [3, "Hard"]]',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'class_style_choices': {
        'is_boolean': False,
        'help_text': 'If set, adds a \'class style\' field to the class creation form. Options are set with the tag, with the value in the JSON format, where the first element of each list is the value stored in the database, and the second value is the option shown on the form (e.g. [["Lecture", "Lecture Style Class"], ["Seminar", "Seminar Style Class"]])',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'volunteer_tshirt_options': {
        'is_boolean': True,
        'help_text': 'Should the volunteer form include t-shirt fields (size and type)?',
        'default': False,
        'category': 'volunteer',
        'is_setting': True,
    },
    'volunteer_tshirt_type_selection': {
        'is_boolean': True,
        'help_text': 'Should the volunteer form include the t-shirt type field?',
        'default': False,
        'category': 'volunteer',
        'is_setting': True,
    },
    'volunteer_shirt_sizes': {
        'is_boolean': False,
        'help_text': 'Comma-separated list of shirt size options for volunteers',
        'default': 'XS, S, M, L, XL, XXL',
        'category': 'volunteer',
        'is_setting': True,
    },
    'volunteer_allow_comments': {
        'is_boolean': True,
        'help_text': 'Should the volunteer form include a comments field?',
        'default': False,
        'category': 'volunteer',
        'is_setting': True,
    },
    'min_available_timeslots': {
        'is_boolean': False,
        'help_text': 'If set, requires teachers to offer availability for at least this many timeslots before allowing them to proceed to registering a class. (Needs to be a plain integer of 0 or higher.)',
        'default': None,
        'category': 'teach',
        'is_setting': True,
        'field': forms.IntegerField(min_value=0),
    },
    'availability_group_timeslots': {
        'is_boolean': True,
        'help_text': 'Should timeslots be grouped into contiguous blocks in the availability interface?',
        'default': True,
        'category': 'teach',
        'is_setting': True,
    },
    'group_phone_number': {
        'is_boolean': False,
        'help_text': 'Phone number that will be displayed on nametags and room rosters',
        'default': None,
        'category': 'manage',
        'is_setting': True,
        'field': forms.CharField(validators=[RegexValidator(r'^(\+\d{1,2}\s?)?1?\-?\.?\s?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$', 'Enter a valid phone number.')])
    },
    'finaid_form_fields': {
        'is_boolean': False,
        'help_text': 'A comma-separated list that specifies which Financial Aid Request fields to include in the form (all fields shown by default)',
        'default': None,
        'category': 'learn',
        'is_setting': True,
    },
    'onsite_classlist_min_refresh': {
        'is_boolean': False,
        'help_text': 'Maximum refresh speed for the onsite classlist to avoid server overload (in seconds).',
        'default': '10',
        'category': 'onsite',
        'is_setting': True,
        'field': forms.IntegerField(min_value=1),
    },
    'oktimes_collapse': {
        'is_boolean': True,
        'help_text': 'Collapse feasible start times into a single column in the Viable Times Spreadsheet?',
        'default': False,
        'category': 'manage',
        'is_setting': True,
    },
    'qsd_display_date_author': {
        'is_boolean': False,
        'help_text': 'Specifies whether to display \'Last modified by [author] on [date] at [time].\' at the bottom of all website pages for non-admins.',
        'default': 'Both',
        'category': 'manage',
        'is_setting': True,
        'field': forms.ChoiceField(choices=[('Both', 'Display author, date, and time'), ('Date', 'Display the date and time but not the author'), ('None', 'Display nothing')]),
    },
    'current_theme_name': {
        'is_boolean': False,
        'help_text': 'The name of the current website theme (should only be modified via the theme settings page)',
        'default': 'default',
        'category': 'theme',
        'is_setting': False,
    },
    'prev_theme_customization': {
        'is_boolean': False,
        'help_text': 'The name of the previous website theme (should only be modified via the theme settings page)',
        'default': 'None',
        'category': 'theme',
        'is_setting': False,
    },
    'current_theme_params': {
        'is_boolean': False,
        'help_text': 'The current theme parameters (should only be modified via the theme settings page)',
        'default': '{}',
        'category': 'theme',
        'is_setting': False,
    },
    'theme_template_control': {
        'is_boolean': False,
        'help_text': 'The current theme settings (should only be modified via the theme settings page)',
        'default': '{}',
        'category': 'theme',
        'is_setting': False,
    },
    'current_theme_palette': {
        'is_boolean': False,
        'help_text': 'The current theme palette (should only be modified via the theme settings page)',
        'default': '{}',
        'category': 'theme',
        'is_setting': False,
    },
    'request_student_phonenum': {
        'is_boolean': True,
        'help_text': 'Whether to request a student home phone number',
        'default': True,
        'category': 'learn',
        'is_setting': True,
    },
    'require_student_phonenum': {
        'is_boolean': True,
        'help_text': 'Whether to require a student phone (home or cell) number',
        'default': True,
        'category': 'learn',
        'is_setting': True,
    },
    'allow_change_grade_level': {
        'is_boolean': True,
        'help_text': 'Should students be allowed to change their grade level in the profile form?',
        'default': False,
        'category': 'learn',
        'is_setting': True,
    },
    'show_studentrep_application': {
        'is_boolean': False,
        'help_text': 'If tag exists, the student-rep application is shown as a part of the student profile. If it exists but is set to \'no_expl\', don\'t show the explanation textbox in the form.',
        'default': None,
        'category': 'learn',
        'is_setting': True,
    },
    'show_student_tshirt_size_options': {
        'is_boolean': True,
        'help_text': 'Show shirt size field in the student profile?',
        'default': False,
        'category': 'learn',
        'is_setting': True,
    },
    'studentinfo_shirt_type_selection': {
        'is_boolean': True,
        'help_text': 'Show shirt type field in the student profile?',
        'default': False,
        'category': 'learn',
        'is_setting': True,
    },
    'student_shirt_sizes': {
        'is_boolean': False,
        'help_text': 'Comma-separated list of shirt size options for students',
        'default': 'XS, S, M, L, XL, XXL',
        'category': 'learn',
        'is_setting': True,
    },
    'show_student_vegetarianism_options': {
        'is_boolean': True,
        'help_text': 'Ask students about their dietary restrictions as part of the student profile?',
        'default': False,
        'category': 'learn',
        'is_setting': True,
    },
    'food_choices': {
        'is_boolean': False,
        'help_text': 'Comma-separated list of food choices for students (requires \'show_student_vegetarianism_options\' to be enabled)',
        'default': 'Anything, Vegetarian, Vegan',
        'category': 'learn',
        'is_setting': True,
    },
    'show_student_graduation_years_not_grades': {
        'is_boolean': True,
        'help_text': 'List graduation years rather than grade numbers in the student profile?',
        'default': False,
        'category': 'learn',
        'is_setting': True,
    },
    'ask_student_about_post_hs_plans': {
        'is_boolean': True,
        'help_text': 'Ask in the student profile about a student\'s post-high-school plans (go to college, go to trade school, get a job, etc)? (deprecated)',
        'default': False,
        'category': 'learn',
        'is_setting': False,
    },
    'ask_student_about_transportation_to_program': {
        'is_boolean': True,
        'help_text': 'Ask in the student profile about how the student is going to get to the upcoming program?',
        'default': False,
        'category': 'learn',
        'is_setting': True,
    },
    'student_medical_needs': {
        'is_boolean': True,
        'help_text': 'Show students a text box where they can enter \'special medical needs\' in the student profile?',
        'default': False,
        'category': 'learn',
        'is_setting': True,
    },
    'require_school_field': {
        'is_boolean': True,
        'help_text': 'Should the \'School\' field be required in the student profile form?',
        'default': False,
        'category': 'learn',
        'is_setting': True,
    },
    'teacherinfo_shirt_options': {
        'is_boolean': True,
        'help_text': 'Include t-shirt fields (size and type) on the teacher profile form?',
        'default': True,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherinfo_shirt_type_selection': {
        'is_boolean': True,
        'help_text': 'Include the t-shirt type field on the teacher profile form? (overrides \'teacherinfo_shirt_options\')',
        'default': True,
        'category': 'teach',
        'is_setting': True,
    },
    'teacher_shirt_sizes': {
        'is_boolean': False,
        'help_text': 'Comma-separated list of shirt size options for teachers',
        'default': 'XS, S, M, L, XL, XXL',
        'category': 'teach',
        'is_setting': True,
    },
    # TODO: For the next five, we probably want to pull the fields from the forms (e.g. TeacherProfileForm.declared_fields.keys())
    # and then use those values in a MultipleChoiceField, but I see two problems:
    # 1) How do we handle the conversion of the list of selected values to a comma-separated string (and back)?
    #    We could maybe check if the field is a MultipleChoiceField, then use getlist on the cleaned_data?
    # 2) We'll probably run into import loops when we try to import the forms
    'teacher_profile_hide_fields': {
        'is_boolean': False,
        'help_text': 'Comma-separated list of fields to hide in the teacher profile form',
        'default': '',
        'category': 'teach',
        'is_setting': True,
    },
    'student_profile_hide_fields': {
        'is_boolean': False,
        'help_text': 'Comma-separated list of fields to hide in the student profile form',
        'default': '',
        'category': 'learn',
        'is_setting': True,
    },
    'volunteer_profile_hide_fields': {
        'is_boolean': False,
        'help_text': 'Comma-separated list of fields to hide in the volunteer profile form',
        'default': '',
        'category': 'volunteer',
        'is_setting': True,
    },
    'educator_profile_hide_fields': {
        'is_boolean': False,
        'help_text': 'Comma-separated list of fields to hide in the educator profile form',
        'default': '',
        'category': 'teach',
        'is_setting': True,
    },
    'guardian_profile_hide_fields': {
        'is_boolean': False,
        'help_text': 'Comma-separated list of fields to hide in the guardian profile form',
        'default': '',
        'category': 'learn',
        'is_setting': True,
    },
    'student_grade_options': {
        'is_boolean': False,
        'help_text': 'A JSON list of grade choices that can be used to override the defaults',
        'default': '[7,8,9,10,11,12]',
        'category': 'learn',
        'is_setting': True,
    },
    'user_types': {
        'is_boolean': False,
        'help_text': 'A JSON list of user types that can be used to override the defaults',
        'default': '[["Student", {"label": "Student (up through 12th grade)", "profile_form": "StudentProfileForm"}],["Teacher", {"label": "Volunteer Teacher", "profile_form": "TeacherProfileForm"}],["Guardian", {"label": "Guardian of Student", "profile_form": "GuardianProfileForm"}],["Educator", {"label": "K-12 Educator", "profile_form": "EducatorProfileForm"}],["Volunteer", {"label": "Onsite Volunteer", "profile_form": "VolunteerProfileForm"}]]',
        'category': 'manage',
        'is_setting': True,
    },
    'student_profile_gender_field': {
        'is_boolean': True,
        'help_text': 'Ask about student gender in profile form?',
        'default': False,
        'category': 'learn',
        'is_setting': True,
    },
    'ask_about_duplicate_accounts': {
        'is_boolean': True,
        'help_text': 'Before creating an account for an email address already in the database, ask if the user wants to log into an existing account instead',
        'default': False,
        'category': 'manage',
        'is_setting': True,
    },
    'require_email_validation': {
        'is_boolean': True,
        'help_text': 'Require users to click on a link in an e-mail sent to their account, before they can use their account?',
        'default': False,
        'category': 'manage',
        'is_setting': True,
    },
    'automatic_registration_redirect': {
        'is_boolean': True,
        'help_text': 'If student/teacher registration is open for exactly one program, redirect to registration after account creation',
        'default': True,
        'category': 'manage',
        'is_setting': True,
    },
    'text_messages_to_students': {
        'is_boolean': True,
        'help_text': 'Ask students if they want to receive text messages about the program, in the student profile',
        'default': False,
        'category': 'learn',
        'is_setting': True,
    },
    'local_state': {
        'is_boolean': False,
        'help_text': 'The default value for state fields in the profile form',
        'default': None,
        'category': 'manage',
        'is_setting': True,
        'field': forms.ChoiceField(required=True, choices=zip(_states,_states))
    },
    'teacher_address_required': {
        'is_boolean': True,
        'help_text': 'Is an address required for a teacher profile?',
        'default': False,
        'category': 'teach',
        'is_setting': True,
    },
    'random_constraints': {
        'is_boolean': False,
        'help_text': 'Constraints for /random in a JSON dictionary (e.g. {"bad_program_names": ["Delve", "SATPrep", "9001", "Test"], "bad_titles": ["Lunch Period"]})',
        'default': '{}',
        'category': 'manage',
        'is_setting': True,
    },
    'admin_home_page': {
        'is_boolean': False,
        'help_text': 'The page to which admins get redirected after logging in (can be a relative or absolute page)',
        'default': None,
        'category': 'manage',
        'is_setting': True,
    },
    'default_restypes': {
        'is_boolean': False,
        'help_text': 'A JSON list of the resource types (by name) to create when making a new program',
        'default': None,
        'category': 'manage',
        'is_setting': True,
    },
    'google_cloud_api_key': {
        'is_boolean': False,
        'help_text': 'An API key for use with the Google Cloud Platform. Used for the student and teacher onsite webapps.',
        'default': '',
        'category': 'manage',
        'is_setting': True,
    },
    'shirt_types': {
        'is_boolean': False,
        'help_text': 'Comma-separated list of shirt type options',
        'default': 'Straight cut, Fitted cut',
        'category': 'manage',
        'is_setting': True,
    },
    'grade_increment_date': {
        'is_boolean': False,
        'help_text': 'When should students\' grades rollover/increment?',
        'default': datetime.date(datetime.date.today().year, 7, 31),
        'category': 'learn',
        'is_setting': True,
        'field': forms.DateField(widget=forms.SelectDateWidget(years=[datetime.date.today().year]))
    },
}

# Any tag used with Tag.getProgramTag()
# or Tag.getBooleanTag() with a program argument
all_program_tags = {
    'increment_default_grade_levels': {
        'is_boolean': True,
        'help_text': 'Consider all students to be one grade level higher (useful for summer programs)',
        'default': False,
        'category': 'learn',
        'is_setting': True,
    },
    'open_class_category': {
        'is_boolean': False,
        'help_text': 'Class category (specified as the ID number) used for open classes (classes for which students don\'t register in advance)',
        'default': None,
        'category': 'learn',
        'is_setting': True,
        'field': forms.IntegerField(min_value=1),
    },
    'sibling_discount': {
        'is_boolean': False,
        'help_text': 'The monitary value of the sibling discount',
        'default': Decimal(0.00),
        'category': 'learn',
        'is_setting': True,
        'field': forms.DecimalField(min_value=Decimal(0.00), decimal_places=2),
    },
    'splashinfo_costs': {
        'is_boolean': False,
        'help_text': 'A JSON structure of food costs for the \'lunchsat\' and \'lunchsun\' keys (must be consistent with all of the options specified in splashinfo_choices)',
        'default': '{}',
        'category': 'learn',
        'is_setting': True,
    },
    'splashinfo_choices': {
        'is_boolean': False,
        'help_text': 'A JSON structure of food options for the \'lunchsat\' and \'lunchsun\' keys (for the SplashInfoModule)',
        'default': None,
        'category': 'learn',
        'is_setting': True,
    },
    'splashinfo_siblingdiscount': {
        'is_boolean': True,
        'help_text': 'Should the sibling discount and sibling name fields be shown in the SplashInfoModule?',
        'default': True,
        'category': 'learn',
        'is_setting': True,
    },
    'splashinfo_lunchsat': {
        'is_boolean': True,
        'help_text': 'Should the Saturday lunch field be shown in the SplashInfoModule?',
        'default': True,
        'category': 'learn',
        'is_setting': True,
    },
    'splashinfo_lunchsun': {
        'is_boolean': True,
        'help_text': 'Should the Sunday lunch field be shown in the SplashInfoModule?',
        'default': True,
        'category': 'learn',
        'is_setting': True,
    },
    'catalog_sort_fields': {
        'is_boolean': False,
        'help_text': 'A comma-separated list of fields by which to sort the course catalog (e.g. \'category__symbol\', \'category__category\', \'sections__meeting_times__start\', \'_num_students\', \'id\')',
        'default': 'category__symbol',
        'category': 'manage',
        'is_setting': True,
    },
    'teacherreg_help_text_duration': {
        'is_boolean': False,
        'help_text': 'If set, overrides the help text for the class registration duration field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_help_text_num_sections': {
        'is_boolean': False,
        'help_text': 'If set, overrides the help text for the class registration number of sections field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_help_text_requested_room': {
        'is_boolean': False,
        'help_text': 'If set, overrides the help text for the class registration requested room field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_help_text_message_for_directors': {
        'is_boolean': False,
        'help_text': 'If set, overrides the help text for the class registration message for directors field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_help_text_purchase_requests': {
        'is_boolean': False,
        'help_text': 'If set, overrides the help text for the class registration purchase requests field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_help_text_class_info': {
        'is_boolean': False,
        'help_text': 'If set, overrides the help text for the class registration class info field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_help_text_class_size_max': {
        'is_boolean': False,
        'help_text': 'If set, overrides the help text for the class registration class size max field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_help_text_class_size_optimal': {
        'is_boolean': False,
        'help_text': 'If set, overrides the help text for the class registration class size optimal field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_help_text_grade_max': {
        'is_boolean': False,
        'help_text': 'If set, overrides the help text for the class registration max grade field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_help_text_grade_min': {
        'is_boolean': False,
        'help_text': 'If set, overrides the help text for the class registration min grade field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_label_duration': {
        'is_boolean': False,
        'help_text': 'If set, overrides the label for the class registration duration field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_label_class_size_max': {
        'is_boolean': False,
        'help_text': 'If set, overrides the label for the class registration class size max field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_label_num_sections': {
        'is_boolean': False,
        'help_text': 'If set, overrides the label for the class registration number of sections field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_label_requested_room': {
        'is_boolean': False,
        'help_text': 'If set, overrides the label for the class registration requested room field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_label_message_for_directors': {
        'is_boolean': False,
        'help_text': 'If set, overrides the label for the class registration message for directors field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_label_purchase_requests': {
        'is_boolean': False,
        'help_text': 'If set, overrides the label for the class registration purchase requests field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_label_class_info': {
        'is_boolean': False,
        'help_text': 'If set, overrides the label for the class registration class info field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_label_class_size_optimal': {
        'is_boolean': False,
        'help_text': 'If set, overrides the label for the class registration class size optimal field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_label_grade_max': {
        'is_boolean': False,
        'help_text': 'If set, overrides the label for the class registration max grade field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_label_grade_min': {
        'is_boolean': False,
        'help_text': 'If set, overrides the label for the class registration min grade field',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_hide_fields': {
        'is_boolean': False,
        'help_text': 'A comma seperated list of what fields (e.g. \'purchase_requests\') you want to hide from teachers during teacher registration',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'teacherreg_default_min_grade': {
        'is_boolean': False,
        'help_text': 'The default minimum grade selected in the class creation/editing form',
        'default': None,
        'category': 'teach',
        'is_setting': True,
        'field': forms.IntegerField(min_value=1),
    },
    'teacherreg_default_max_grade': {
        'is_boolean': False,
        'help_text': 'The default maximum grade selected in the class creation/editing form',
        'default': None,
        'category': 'teach',
        'is_setting': True,
        'field': forms.IntegerField(min_value=1),
    },
    'teacherreg_default_class_size_max': {
        'is_boolean': False,
        'help_text': 'The default class size max in the class creation/editing form',
        'default': None,
        'category': 'teach',
        'is_setting': True,
        'field': forms.IntegerField(min_value=1),
    },
    'stripe_settings': {
        'is_boolean': False,
        'help_text': 'Settings for the Stripe Credit Card Module (JSON dictionary with values for any number of the following keys: "donation_text" (invoice line item), "donation_options" (list of donation dollar amount options), "offer_donation" (boolean for whether to prompt for a donation to LU), and "invoice_prefix" (prefix for invoice line item)',
        'default': '{}',
        'category': 'learn',
        'is_setting': True,
    },
    'learn_extraform_id': {
        'is_boolean': False,
        'help_text': 'Form ID of the custom form used for student registration',
        'default': None,
        'category': 'learn',
        'is_setting': True,
        'field': forms.IntegerField(min_value=1),
    },
    'teach_extraform_id': {
        'is_boolean': False,
        'help_text': 'Form ID of the custom form used for teacher registration',
        'default': None,
        'category': 'teach',
        'is_setting': True,
        'field': forms.IntegerField(min_value=1),
    },
    'donation_settings': {
        'is_boolean': False,
        'help_text': 'Settings for the Donation Module (JSON dictionary with values for any number of the following keys: "donation_text" (invoice line item) and "donation_options" (list of donation dollar amount options)',
        'default': '{}',
        'category': 'learn',
        'is_setting': True,
    },
    'no_overlap_classes': {
        'is_boolean': False,
        'help_text': 'A list of classes that the Scheduling Check Module checks aren\'t overlapping. The tag should contain a dict of {"comment": [list,of,class,ids]}',
        'default': '{}',
        'category': 'manage',
        'is_setting': True,
    },
    'special_classroom_types': {
        'is_boolean': False,
        'help_text': 'A dictionary mapping resource request type desired_value regexes to a list of classrooms (by resource ID)',
        'default': '{}',
        'category': 'manage',
        'is_setting': True,
    },
    'collapse_full_classes': {
        'is_boolean': True,
        'help_text': 'Should full classes be collapsed in the catalog/student registration?',
        'default': True,
        'category': 'learn',
        'is_setting': True,
    },
    'friendly_times_with_date': {
        'is_boolean': True,
        'help_text': 'Should dates be included when displaying class details?',
        'default': False,
        'category': 'learn',
        'is_setting': True,
    },
    'grade_range_popup': {
        'is_boolean': True,
        'help_text': 'If selected grade min and grade max are at least 4 grades apart, show a popup for teachers',
        'default': True,
        'category': 'teach',
        'is_setting': True,
    },
    'quiz_form_id': {
        'is_boolean': False,
        'help_text': 'The ID of the customform to associate with the Teacher Quiz Module',
        'default': None,
        'category': 'teach',
        'is_setting': True,
        'field': forms.IntegerField(min_value=1),
    },
    'display_registration_names': {
        'is_boolean': False,
        'help_text': 'Which registration types (in addition to "Enrolled") should be included in the inline student schedule? (JSON list)',
        'default': None,
        'category': 'learn',
        'is_setting': True,
    },
    'program_size_by_grade': {
        'is_boolean': False,
        'help_text': 'A JSON dictionary specifying the program capacities for grades or grade ranges (e.g. {"7-8": 1000, "9": 300, "10-12": 1500})',
        'default': None,
        'category': 'learn',
        'is_setting': True,
    },
    'grade_ranges': {
        'is_boolean': False,
        'help_text': 'JSON list of grade ranges that replace min and max grade options in teacher class reg (e.g. "[[7,9],[9,10],[9,12],[10,12],[11,12]]")',
        'default': None,
        'category': 'teach',
        'is_setting': True,
    },
    'studentschedule_show_empty_blocks': {
        'is_boolean': True,
        'help_text': 'Should student schedules include time slots for which students have no classes?',
        'default': False,
        'category': 'learn',
        'is_setting': True,
    },
    'student_lottery_run': {
        'is_boolean': True,
        'help_text': 'Has the Phase Zero Student Lottery been run?',
        'default': False,
        'category': 'learn',
        'is_setting': False,
    },
    'formstack_id': {
        'is_boolean': False,
        'help_text': 'Formstack form ID for the Formstack MedLiab Module',
        'default': None,
        'category': 'learn',
        'is_setting': True,
    },
    'formstack_viewkey': {
        'is_boolean': False,
        'help_text': 'Formstack form viewing key for the Formstack MedLiab Module',
        'default': None,
        'category': 'learn',
        'is_setting': True,
    },
    'autoscheduler_constraint_overrides': {
        'is_boolean': False,
        'help_text': 'See the autoscheduler module for details',
        'default': '{}',
        'category': 'manage',
        'is_setting': True,
    },
    'autoscheduler_scorer_weight_overrides': {
        'is_boolean': False,
        'help_text': 'See the autoscheduler module for details',
        'default': '{}',
        'category': 'manage',
        'is_setting': True,
    },
    'autoscheduler_resource_constraint_overrides': {
        'is_boolean': False,
        'help_text': 'See the autoscheduler module for details',
        'default': '{}',
        'category': 'manage',
        'is_setting': True,
    },
    'autoscheduler_resource_scoring_overrides': {
        'is_boolean': False,
        'help_text': 'See the autoscheduler module for details',
        'default': '{}',
        'category': 'manage',
        'is_setting': True,
    },
    'num_stars': {
        'is_boolean': False,
        'help_text': 'The preferred number of starred classes per timeslot for student two-phase registration',
        'default': '10',
        'category': 'learn',
        'is_setting': True,
        'field': forms.IntegerField(min_value=1),
    },
    'survey_teacher_filter': {
        'is_boolean': False,
        'help_text': 'Which sets of teachers are allowed to fill out the post-program survey? Specified as a comma-separated list of options in program.teachers().',
        'default': 'class_submitted',
        'category': 'teach',
        'is_setting': True,
    },
    'survey_student_filter': {
        'is_boolean': False,
        'help_text': 'Which sets of students are allowed to fill out the post-program survey? Specified as a comma-separated list of options in program.students().',
        'default': 'classreg',
        'category': 'learn',
        'is_setting': True,
    },
    'volunteer_help_text_comments': {
        'is_boolean': False,
        'help_text': 'If set, overrides the help text for the comments field for the volunteer form',
        'default': None,
        'category': 'volunteer',
        'is_setting': True,
    },
    'volunteer_require_auth': {
        'is_boolean': True,
        'help_text': 'Do volunteers need to have accounts before signing up? (If not, one will be created when they sign up)',
        'default': False,
        'category': 'volunteer',
        'is_setting': True,
    },
    'program_center': {
        'is_boolean': False,
        'help_text': 'The geographic center for a program, following the form {lat: 37.427490, lng: -122.170267}. Used for the teacher and student onsite webapps.',
        'default': '{lat: 37.427490, lng: -122.170267}',
        'category': 'manage',
        'is_setting': True,
    },
    'student_webapp_isstep': {
        'is_boolean': True,
        'help_text': 'Should the student onsite webapp be shown as a step in student registration?',
        'default': False,
        'category': 'learn',
        'is_setting': True,
    },
    'teacher_webapp_isstep': {
        'is_boolean': True,
        'help_text': 'Should the teacher onsite webapp be shown as a step in teacher registration?',
        'default': False,
        'category': 'teach',
        'is_setting': True,
    },
    'switch_time_program_attendance': {
        'is_boolean': False,
        'help_text': 'At what time should the student onsite webapp use program attendance if available (instead of enrollment) to determine if a class is full? If blank, program attendance numbers will not be used. Format: HH:MM where HH is in 24 hour time.',
        'default': None,
        'category': 'learn',
        'is_setting': True,
    },
    'switch_lag_class_attendance': {
        'is_boolean': False,
        'help_text': 'How many minutes into a class should the student onsite webapp use class attendance numbers if available (instead of enrollment or program attendance) to determine if a class is full? If blank, class attendance numbers will not be used.',
        'default': None,
        'category': 'learn',
        'is_setting': True,
        'field': forms.IntegerField(min_value=0),
    },
    'student_lottery_group_max': {
        'is_boolean': False,
        'help_text': 'What is the maximum number of students that can be in the same lottery group? (set to 1 to not allow groups)',
        'default': 4,
        'category': 'learn',
        'is_setting': True,
        'field': forms.IntegerField(min_value=1),
    },
    'student_survey_isstep': {
        'is_boolean': True,
        'help_text': 'Should the student survey be shown as a step in student registration once the event has started?',
        'default': False,
        'category': 'learn',
        'is_setting': True,
    },
    'teacher_survey_isstep': {
        'is_boolean': True,
        'help_text': 'Should the teacher survey be shown as a step in teacher registration once the event has started?',
        'default': False,
        'category': 'teach',
        'is_setting': True,
    },
    'teacher_onsite_checkin_note': {
        'is_boolean': False,
        'help_text': 'The message that is shown at the top of the teacher webapp schedule when a teacher is NOT checked in.',
        'default': 'Note: Please make sure to check in before your first class today.',
        'category': 'teach',
        'is_setting': True,
    },
    'availability_group_tolerance': {
        'is_boolean': False,
        'help_text': 'Time blocks must be less than this many minutes apart to be shown as contiguous for the availability module(s). This will not impact the calculation of possible class durations (see the "Timeblock contiguous tolerance" tag below).',
        'default': '20',
        'category': 'teach',
        'is_setting': True,
        'field': forms.IntegerField(min_value=0),
    },
    'timeblock_contiguous_tolerance': {
        'is_boolean': False,
        'help_text': 'Time blocks must be less than this many minutes apart to be considered contiguous for a single class.',
        'default': '20',
        'category': 'teach',
        'is_setting': True,
        'field': forms.IntegerField(min_value=0),
    },
    'moderator_title': {
        'is_boolean': False,
        'help_text': 'The name used to refer to a section moderator throughout the website.',
        'default': 'Moderator',
        'category': 'teach',
        'is_setting': True,
    },
}

# Dictionary of categories that tags fall into (for grouping on the tag settings page)
# Each key is the string in the tuples above, each value is the human-readable string that will be shown in the template/form
tag_categories = {
    'teach': 'Teacher Registration Settings',
    'learn': 'Student Registration Settings',
    'manage': 'General Management Settings',
    'onsite': 'Onsite Settings',
    'volunteer': 'Volunteer Registration Settings',
    'theme': 'Theme Settings',
}
