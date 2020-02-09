# Lists of all tags used anywhere in the codebase
# Populated by hand, so don't be too surprised if something
# is missing

# Format: 'key': (is tag used with getBooleanTag?, "some help text for admins", default value, category, show on tag settings page?)
# Category options are in a dictionary below

# Any tag used with Tag.getTag(),
# or Tag.getBooleanTag() with no program argument
all_global_tags = {
    'teacherreg_custom_forms': (False, "JSON list of names of teacher registration custom forms to include in the class registration form", None, "teach", True),
    'allow_global_restypes': (True, "Include global resource types in the manage resources and teacher registration options", False, "teach", True),
    'full_group_name': (False, "For places that demand an official-sounding name for the group that goes beyond the INSTITUTION_NAME and ORGANIZATION_SHORT_NAME settings.", None, "manage", True),
    'nearly_full_threshold': (False, "Fraction (as a decimal) of section capacity that determines if a class is 'nearly full'", 0.75, "teach", True),
    'use_class_size_optimal': (True, "Should teachers be asked for an optimal class size (instead of maximum size)? Must be set to True for optimal class size options in the class registration module info to have any effect.", False, "teach", True),
    'teacherreg_difficulty_choices': (False, "This controls the choices of the 'Difficulty' field on the class creation/editing form. This should be a JSON-formatted list of 2-element lists. Example: '[[1, 'Easy'], [2, 'Medium'], [3, 'Hard']]'", None, "teach", True),
    'class_style_choices': (False, "If set, adds a 'class style' field to the class creation form. Options are set with the tag, with the value in the JSON format, where the first element of each list is the value stored in the database, and the second value is the option shown on the form (e.g. [['Lecture', 'Lecture Style Class'], ['Seminar', 'Seminar Style Class']])", None, "teach", True),
    'volunteer_tshirt_options': (True, "Should the volunteer form include t-shirt fields (size and type)?", False, "volunteer", True),
    'volunteer_tshirt_type_selection': (True, "Should the volunteer form include the t-shirt type field?", False, "volunteer", True),
    'volunteer_allow_comments': (True, "Should the volunteer form include a comments field?", None, "volunteer", False),
    'min_available_timeslots': (False, "If set, requires teachers to offer availability for at least this many timeslots before allowing them to proceed to registering a class. (Needs to be a plain integer of 0 or higher.)", None, "teach", True),
    'availability_group_timeslots': (True, "Should timeslots be grouped into contiguous blocks in the availability interface?", True, "teach", True),
    'group_phone_number': (False, "Phone number that will be displayed on nametags and room rosters", None, "manage", True),
    'finaid_form_fields': (False, "A comma-separated list that specifies which of which Financial Aid Request fields to include in the form (all fields shown by default)", None, "learn", True),
    'onsite_classlist_min_refresh': (False, "Maximum refresh speed for the onsite classlist to avoid server overload.", '10', "onsite", True),
    'oktimes_collapse': (True, "If set, collapses feasible start times into a single column in the Viable Times Spreadsheet", False, "manage", True),
    'qsd_display_date_author': (False, "Specifies whether to display 'Last modified by [author] on [date] at [time].' at the bottom of all website pages for non-admins. Set to 'Both' (without the single quotes) to display author and date; set to 'Date' to display the date and time but not the author; set to 'None' to display nothing.", "Both", "manage", True),
    'current_theme_name': (False, "The name of the current website theme (should only be modified via the theme settings page)", "default", "theme", False),
    'prev_theme_customization': (False, "The name of the previous website theme (should only be modified via the theme settings page)", "None", "theme", False),
    'current_theme_params': (False, "The current theme parameters (should only be modified via the theme settings page)", "{}", "theme", False),
    'theme_template_control': (False, "The current theme settings (should only be modified via the theme settings page)", "{}", "theme", False),
    'current_theme_palette': (False, "The current theme palette (should only be modified via the theme settings page)", "{}", "theme", False),
    'request_student_phonenum': (True, "Whether to request a student home phone number", True, "learn", True),
    'require_student_phonenum': (True, "Whether to require a student phone (home or cell) number", True, "learn", True),
    'allow_change_grade_level': (True, "Should students be allowed to change their grade level in the profile form?", False, "learn", True),
    'show_studentrep_application': (False, "If tag exists, the student-rep application is shown as a part of the student profile. If it exists but is set to 'no_expl', don't show the explanation textbox in the form.", None, "learn", True),
    'show_student_tshirt_size_options': (False, "If tag exists, ask students about their choice of T-shirt size as part of the student profile", None, "learn", True), #should probably be a boolean
    'studentinfo_shirt_type_selection': (False, "If set to 'False', hides shirt type field in the student profile", None, "learn", True), #should probably be a boolean
    'show_student_vegetarianism_options': (False, "If tag exists, ask students about their dietary restrictions as part of the student profile", None, "learn", True), #should probably be a boolean
    'show_student_graduation_years_not_grades': (True, "If tag exists, list graduation years rather than grade numbers in the student profile", None, "learn", True), #default should probably be False
    'ask_student_about_post_hs_plans':  (True, "If tag exists, ask in the student profile about a student's post-high-school plans (go to college, go to trade school, get a job, etc) (not implemented yet)", None, "learn", False),
    'ask_student_about_transportation_to_program': (False, "If tag exists, ask in the student profile about how the student is going to get to the upcoming program", None, "learn", True), #should probably be a boolean
    'student_medical_needs': (False, "If tag exists, students will see a text box where they can enter 'special medical needs'", None, "learn", True), #should probably be a boolean
    'require_school_field': (True, "Should the 'School' field be required in the student profile form?", False, "learn", True), #default is None in one use in user_profile.py
    'teacherinfo_shirt_options': (False, "If set to 'False', the teacher form does not include any t-shirt fields (size and type)", None, "teach", True), #should probably be a boolean
    'teacherinfo_shirt_type_selection': (False, "If set to 'False', the teacher form does not include the t-shirt type field", None, "teach", True), #default should probably be False
    'teacher_profile_hide_fields': (False, "Comma-separated list of fields to hide in the teacher profile form", "", "teach", True),
    'student_grade_options': (False, "A JSON list of grade choices that can be used to override the defaults", "[7,8,9,10,11,12]", "learn", True),
    'user_types': (False, "A JSON list of user types that can be used to override the defaults", "[['Student', {'label': 'Student (up through 12th grade)', 'profile_form': 'StudentProfileForm'}],['Teacher', {'label': 'Volunteer Teacher', 'profile_form': 'TeacherProfileForm'}],['Guardian', {'label': 'Guardian of Student', 'profile_form': 'GuardianProfileForm'}],['Educator', {'label': 'K-12 Educator', 'profile_form': 'EducatorProfileForm'}],['Volunteer', {'label': 'Onsite Volunteer', 'profile_form': 'VolunteerProfileForm'}]]", "manage", True),
    'studentinfo_shirt_options': (False, "Should the tshirt info in student infos populate the student profile form? (use with 'show_student_tshirt_size_options')", None, "learn", True), #why is this a separate tag? should probably be boolean
    'studentinfo_food_options': (False, "Should the food preference info in student infos populate the student profile form? (use with 'show_student_vegetarianism_options')", None, "learn", True), #why is this a separate tag? should probably be boolean),
    'student_profile_gender_field': (True, "Ask about student gender in profile form?", None, "learn", True), #default should probably be False
    'ask_about_duplicate_accounts': (True, "Before creating an account for an email address already in the database, ask if the user wants to log into an existing account instead", False, "manage", True),
    'require_email_validation': (True, "Require users to click on a link in an e-mail sent to their account, before they can use their account?", False, "manage", True),
    'automatic_registration_redirect': (True, "If student/teacher registration is open for exactly one program, redirect to registration after account creation", True, "manage", True),
    'text_messages_to_students': (True, "Ask students if they want to receive text messages about the program, in the student profile", None, "learn", True), #default should probably be False
    'local_state': (False, "The default value for state fields in the profile form (not implemented)", None, "manage", False), #pretty sure this is not actually implemented
    'teacher_address_required': (True, "Is an address required for a teacher profile?", False, "teach", True),
    'random_constraints': (False, "Constraints for /random in a JSON dictionary (e.g. {'bad_program_names': ['Delve', 'SATPrep', '9001', 'Test'], 'bad_titles': ['Lunch Period']})", "{}", "manage", True),
    'admin_home_page': (False, "The page to which admins get redirected after logging in (can be a relative or absolute page)", None, "manage", True),
}

# Any tag used with Tag.getProgramTag(),
# or Tag.getBooleanTag() with a program argument
all_program_tags = {
    'increment_default_grade_levels': (True, "Consider all students to be one grade level higher (useful for summer programs)", False, "learn", True),
    'open_class_category': (False, "Class category (specified as the ID number) used for open classes (classes for which students don't register in advance)", None, "learn", True),
    'sibling_discount': (False, "The monitary value of the sibling discount", '0.00', "learn", True),
    'splashinfo_costs': (False, "A JSON structure of food costs for the 'lunchsat' and 'lunchsun' keys (must be consistent with all of the options specified in splashinfo_choices)", '{}', "learn", True),
    'splashinfo_choices': (False, "A JSON structure of food options for the 'lunchsat' and 'lunchsun' keys (for the SplashInfoModule)", None, "learn", True),
    'splashinfo_siblingdiscount': (True, "Should the sibling discount and sibling name fields be shown in the SplashInfoModule?", True, "learn", True),
    'splashinfo_lunchsat': (True, "Should the Saturday lunch field be shown in the SplashInfoModule?", True, "learn", True),
    'splashinfo_lunchsun': (True, "Should the Sunday lunch field be shown in the SplashInfoModule?", True, "learn", True),
    'catalog_sort_fields': (False, "A comma-separated list of fields by which to sort the catalog", "varies by module", "manage", True),
    'teacherreg_help_text_duration': (False, "Help text for the class registration duration field", None, "teach", True),
    'teacherreg_help_text_num_sections': (False, "Help text for the class registration number of sections field", None, "teach", True),
    'teacherreg_help_text_requested_room': (False, "Help text for the class registration requested room field", None, "teach", True),
    'teacherreg_help_text_message_for_directors': (False, "Help text for the class registration message for directors field", None, "teach", True),
    'teacherreg_help_text_purchase_requests': (False, "Help text for the class registration purchase requests field", None, "teach", True),
    'teacherreg_help_text_class_info': (False, "Help text for the class registration class info field", None, "teach", True),
    'teacherreg_help_text_class_size_max': (False, "Help text for the class registration class size max field", None, "teach", True),
    'teacherreg_help_text_class_size_optimal': (False, "Help text for the class registration class size optimal field", None, "teach", True),
    'teacherreg_help_text_grade_max': (False, "Help text for the class registration max grade field", None, "teach", True),
    'teacherreg_help_text_grade_min': (False, "Help text for the class registration min grade field", None, "teach", True),
    'teacherreg_label_duration': (False, "Label for the class registration duration field", None, "teach", True),
    'teacherreg_label_class_size_max': (False, "Label for the class registration class size max field", None, "teach", True),
    'teacherreg_label_num_sections': (False, "Label for the class registration number of sections field", None, "teach", True),
    'teacherreg_label_requested_room': (False, "Label for the class registration requested room field", None, "teach", True),
    'teacherreg_label_message_for_directors': (False, "Label for the class registration message for directors field", None, "teach", True),
    'teacherreg_label_purchase_requests': (False, "Label for the class registration purchase requests field", None, "teach", True),
    'teacherreg_label_class_info': (False, "Label for the class registration class info field", None, "teach", True),
    'teacherreg_label_class_size_optimal': (False, "Label for the class registration class size optimal field", None, "teach", True),
    'teacherreg_label_grade_max': (False, "Label for the class registration max grade field", None, "teach", True),
    'teacherreg_label_grade_min': (False, "Label for the class registration min grade field", None, "teach", True),
    'teacherreg_hide_fields': (False, "A comma seperated list of what fields (i.e. purchase_requests) you want to hide from teachers during teacher registration", None, "teach", True),
    'teacherreg_default_min_grade': (False, "The default minimum grade selected in the class creation/editing form", None, "teach", True),
    'teacherreg_default_max_grade': (False, "The default maximum grade selected in the class creation/editing form", None, "teach", True),
    'teacherreg_default_class_size_max': (False, "The default class size max in the class creation/editing form", None, "teach", True),
    'stripe_settings': (False, "Settings for the Stripe Credit Card Module (JSON dictionary with values for any number of the following keys: 'donation_text' (invoice line item), 'donation_options' (list of donation dollar amount options), 'offer_donation' (boolean for whether to prompt for a donation to LU), and 'invoice_prefix' (prefix for invoice line item)", "{}", "learn", True),
    'learn_extraform_id': (False, "Form ID of the custom form used for student registration", None, "learn", True),
    'teach_extraform_id': (False, "Form ID of the custom form used for teacher registration", None, "teach", True),
    'donation_settings': (False, "Settings for the Donation Module (JSON dictionary with values for any number of the following keys: 'donation_text' (invoice line item) and 'donation_options' (list of donation dollar amount options)", "{}", "learn", True),
    'no_overlap_classes': (False, "A list of classes that the Scheduling Check Module checks aren't overlapping. The tag should contain a dict of {'comment': [list,of,class,ids]}", "{}", "manage", True),
    'special_classroom_types': (False, "A dictionary mapping resource request type desired_value regexes to a list of classrooms (by resource ID)", "{}", "manage", True),
    'collapse_full_classes': (True, "Should full classes be collapsed in the catalog/student registration?", True, "learn", True),
    'friendly_times_with_date': (True, "Should dates be included when displaying class details?", False, "learn", True),
    'grade_range_popup': (True, "If selected grade min and grade max are at least 4 grades apart, show a popup for teachers", True, "teach", True),
    'quiz_form_id': (False, "The ID of the customform to associate with the Teacher Quiz Module", None, "teach", True),
    'default_restypes': (False, "A JSON list of the resource types (by name) to create when making a new program", None, "manage", True), #doesn't really make much sense to have this be a program tag, since you'd need to set it before creating the program?
    'cc_redirect': (False, "After credit card payment, to which page should we direct students? May be relative to the program URL (e.g. confirmreg, studentreg, etc.) or relative or full URLs may be used (e.g. https://www.google.com, /learn/thanks.html, etc.) (deprecated)", "confirmreg", "learn", False), #depricated??
    'display_registration_names': (False, "Which registration types should be displayed in addition to 'Enrolled'?", None, "learn", True),
    'program_size_by_grade': (False, "A JSON dictionary specifying the program capacities for grades or grade ranges (e.g. {'7-8': 1000, '9': 300, '10-12': 1500})", None, "learn", True),
    'grade_ranges': (False, "JSON list of grade ranges that replace min and max grade options in teacher class reg (e.g. '[[7,9],[9,10],[9,12],[10,12],[11,12]]')", None, "teach", True),
    'studentschedule_show_empty_blocks': (True, "Should student schedules include time slots for which students have no classes?", False, "learn", True), #default is None in programprintables.py
    'student_lottery_run': (True, "Has the Phase Zero Student Lottery been run?", False, "learn", False),
    'formstack_id': (False, "Formstack form ID for the Formstack MedLiab Module", None, "learn", True),
    'formstack_viewkey': (False, "Formstack form viewing key for the Formstack MedLiab Module", None, "learn", True),
    'autoscheduler_constraint_overrides': (False, "See the autoscheduler for details", "{}", "manage", True),
    'autoscheduler_scorer_weight_overrides': (False, "See the autoscheduler for details", "{}", "manage", True),
    'autoscheduler_resource_constraint_overrides': (False, "See the autoscheduler for details", "{}", "manage", True),
    'autoscheduler_resource_scoring_overrides': (False, "See the autoscheduler for details", "{}", "manage", True),
    'num_stars': (False, "The preferred number of starred classes per timeslot for student two-phase registration", 10, "learn", True),
    'survey_teacher_filter': (False, "Which sets of teachers are allowed to fill out the post-program survey? Specified as a comma-separated list of options in program.teachers().", "class_submitted", "teach", True),
    'survey_student_filter': (False, "Which sets of students are allowed to fill out the post-program survey? Specified as a comma-separated list of options in program.students().", "classreg", "learn", True),
    'volunteer_help_text_comments': (False, "If set, overrides the help text for the comments field for the volunteer form", None, "volunteer", True),
    'volunteer_require_auth': (True, "Do volunteers need to have accounts before signing up? (If not, one will be created when they sign up)", False, "volunteer", True),
}

# Dictionary of categories that tags fall into (for grouping on the tag settings page)
# Each key is the string in the tuples above, each value is the human-readable string that will be shown in the template/form
tag_categories = {
    'teach': "Teacher Registration Settings",
    'learn': "Student Registration Settings",
    'manage': "General Management Settings",
    'onsite': "Onsite Settings",
    'volunteer': "Volunteer Registration Settings",
    'theme': "Theme Settings",
}
