from esp.program.modules.models import ProgramModuleObj, DBReceipt, StudentClassRegModuleInfo, ClassRegModuleInfo, RemoteProfile, SATPrepTeacherModuleInfo, CreditCardSettings, AJAXChangeLogEntry, AJAXChangeLog
from anonymizer import Anonymizer

class ProgramModuleObjAnonymizer(Anonymizer):

    model = ProgramModuleObj

    attributes = [
        ('id', "SKIP"),
        ('program_id', "SKIP"),
        ('module_id', "SKIP"),
        ('seq', "integer"),
        ('required', "bool"),
        ('required_label', "varchar"),
    ]


class DBReceiptAnonymizer(Anonymizer):

    model = DBReceipt

    attributes = [
        ('id', "SKIP"),
        ('action', "varchar"),
        ('program_id', "SKIP"),
        ('receipt', "lorem"),
    ]


class StudentClassRegModuleInfoAnonymizer(Anonymizer):

    model = StudentClassRegModuleInfo

    attributes = [
        ('id', "SKIP"),
        ('module_id', "SKIP"),
        ('enforce_max', "bool"),
        ('class_cap_multiplier', "decimal"),
        ('class_cap_offset', "integer"),
        ('apply_multiplier_to_room_cap', "bool"),
        ('signup_verb_id', "SKIP"),
        ('use_priority', "bool"),
        ('priority_limit', "integer"),
        ('use_grade_range_exceptions', "bool"),
        ('register_from_catalog', "bool"),
        ('visible_enrollments', "bool"),
        ('visible_meeting_times', "bool"),
        ('show_unscheduled_classes', "bool"),
        ('confirm_button_text', "varchar"),
        ('view_button_text', "varchar"),
        ('cancel_button_text', "varchar"),
        ('temporarily_full_text', "varchar"),
        ('cancel_button_dereg', "bool"),
        ('progress_mode', "integer"),
        ('send_confirmation', "bool"),
        ('show_emailcodes', "bool"),
        ('force_show_required_modules', "bool"),
    ]


class ClassRegModuleInfoAnonymizer(Anonymizer):

    model = ClassRegModuleInfo

    attributes = [
        ('id', "SKIP"),
        ('module_id', "SKIP"),
        ('allow_coteach', "bool"),
        ('set_prereqs', "bool"),
        ('display_times', "bool"),
        ('times_selectmultiple', "bool"),
        ('class_max_duration', "integer"),
        ('class_min_cap', "integer"),
        ('class_max_size', "integer"),
        ('class_size_step', "integer"),
        ('class_other_sizes', "varchar"),
        ('director_email', "email"),
        ('class_durations', "varchar"),
        ('teacher_class_noedit', "datetime"),
        ('allowed_sections', "varchar"),
        ('session_counts', "varchar"),
        ('num_teacher_questions', "positive_integer"),
        ('num_class_choices', "positive_integer"),
        ('color_code', "varchar"),
        ('allow_lateness', "bool"),
        ('ask_for_room', "bool"),
        ('use_class_size_max', "bool"),
        ('use_class_size_optimal', "bool"),
        ('use_optimal_class_size_range', "bool"),
        ('use_allowable_class_size_ranges', "bool"),
        ('open_class_registration', "bool"),
        ('progress_mode', "integer"),
    ]


class RemoteProfileAnonymizer(Anonymizer):

    model = RemoteProfile

    attributes = [
        ('id', "SKIP"),
        ('user_id', "SKIP"),
        ('program_id', "SKIP"),
        ('volunteer', "bool"),
        ('need_bus', "bool"),
    ]


class SATPrepTeacherModuleInfoAnonymizer(Anonymizer):

    model = SATPrepTeacherModuleInfo

    attributes = [
        ('id', "SKIP"),
        ('sat_math', "positive_integer"),
        ('sat_writ', "positive_integer"),
        ('sat_verb', "positive_integer"),
        ('mitid', "positive_integer"),
        ('subject', "choice"),
        ('user_id', "SKIP"),
        ('program_id', "SKIP"),
        ('section', "varchar"),
    ]


class CreditCardSettingsAnonymizer(Anonymizer):

    model = CreditCardSettings

    attributes = [
        ('id', "SKIP"),
        ('module_id', "SKIP"),
        ('store_id', "varchar"),
        ('host_payment_form', "bool"),
        ('post_url', "varchar"),
        ('offer_donation', "bool"),
        ('invoice_prefix', "varchar"),
    ]


class AJAXChangeLogEntryAnonymizer(Anonymizer):

    model = AJAXChangeLogEntry

    attributes = [
        ('id', "SKIP"),
        ('index', "integer"),
        ('timeslots', "varchar"),
        ('room_name', "name"),
        ('cls_id', "integer"),
        ('user_id', "SKIP"),
        ('time', "SKIP"),
    ]


class AJAXChangeLogAnonymizer(Anonymizer):

    model = AJAXChangeLog

    attributes = [
        ('id', "SKIP"),
        ('program_id', "SKIP"),
    ]
