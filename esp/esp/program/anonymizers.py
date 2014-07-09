from esp.program.models import ProgramModule, ArchiveClass, Program, SplashInfo, RegistrationProfile, TeacherBio, FinancialAidRequest, BooleanToken, BooleanExpression, ScheduleConstraint, ScheduleTestTimeblock, ScheduleTestOccupied, ScheduleTestCategory, ScheduleTestSectionList, VolunteerRequest, VolunteerOffer, RegistrationType, StudentRegistration, StudentSubjectInterest, ClassSizeRange, ProgramCheckItem, ClassSection, ClassSubject, ClassImplication, ClassCategories, StudentAppQuestion, StudentAppResponse, StudentAppReview, StudentApplication, ClassFlagType, ClassFlag
from anonymizer import Anonymizer

class ProgramModuleAnonymizer(Anonymizer):

    model = ProgramModule

    attributes = [
        ('id', "SKIP"),
        ('link_title', "varchar"),
        ('admin_title', "varchar"),
        ('inline_template', "varchar"),
        ('module_type', "varchar"),
        ('handler', "varchar"),
        ('seq', "integer"),
        ('required', "bool"),
    ]


class ArchiveClassAnonymizer(Anonymizer):

    model = ArchiveClass

    attributes = [
        ('id', "SKIP"),
        ('program', "varchar"),
        ('year', "varchar"),
        ('date', "varchar"),
        ('category', "varchar"),
        ('teacher', "varchar"),
        ('title', "varchar"),
        ('description', "lorem"),
        ('teacher_ids', "varchar"),
        ('student_ids', "lorem"),
        ('original_id', "integer"),
        ('num_old_students', "integer"),
    ]


class ProgramAnonymizer(Anonymizer):

    model = Program

    attributes = [
        ('id', "SKIP"),
        ('anchor_id', "SKIP"),
        ('url', "varchar"),
        ('name', "name"),
        ('grade_min', "integer"),
        ('grade_max', "integer"),
        ('director_email', "email"),
        ('director_cc_email', "email"),
        ('director_confidential_email', "email"),
        ('program_size_max', "integer"),
        ('program_allow_waitlist', "bool"),
    ]


class SplashInfoAnonymizer(Anonymizer):

    model = SplashInfo

    attributes = [
        ('id', "SKIP"),
        ('student_id', "SKIP"),
        ('program_id', "SKIP"),
        ('lunchsat', "varchar"),
        ('lunchsun', "varchar"),
        ('siblingdiscount', "bool"),
        ('siblingname', "varchar"),
        ('submitted', "bool"),
    ]


class RegistrationProfileAnonymizer(Anonymizer):

    model = RegistrationProfile

    attributes = [
        ('id', "SKIP"),
        ('user_id', "SKIP"),
        ('program_id', "SKIP"),
        ('contact_user_id', "SKIP"),
        ('contact_guardian_id', "SKIP"),
        ('contact_emergency_id', "SKIP"),
        ('student_info_id', "SKIP"),
        ('teacher_info_id', "SKIP"),
        ('guardian_info_id', "SKIP"),
        ('educator_info_id', "SKIP"),
        ('last_ts', "datetime"),
        ('emailverifycode', "email"),
        ('email_verified', "bool"),
        ('most_recent_profile', "bool"),
        ('old_text_reminder', "bool"),
    ]


class TeacherBioAnonymizer(Anonymizer):

    model = TeacherBio

    attributes = [
        ('id', "SKIP"),
        ('program_id', "SKIP"),
        ('user_id', "SKIP"),
        ('bio', "lorem"),
        ('slugbio', "varchar"),
        ('picture', "SKIP"),
        ('picture_height', "integer"),
        ('picture_width', "integer"),
        ('last_ts', "datetime"),
    ]


class FinancialAidRequestAnonymizer(Anonymizer):

    model = FinancialAidRequest

    attributes = [
        ('id', "SKIP"),
        ('program_id', "SKIP"),
        ('user_id', "SKIP"),
        ('reduced_lunch', "bool"),
        ('household_income', "varchar"),
        ('extra_explaination', "lorem"),
        ('student_prepare', "bool"),
        ('done', "bool"),
    ]


class BooleanTokenAnonymizer(Anonymizer):

    model = BooleanToken

    attributes = [
        ('id', "SKIP"),
        ('exp_id', "SKIP"),
        ('text', "lorem"),
        ('seq', "integer"),
    ]


class BooleanExpressionAnonymizer(Anonymizer):

    model = BooleanExpression

    attributes = [
        ('id', "SKIP"),
        ('label', "varchar"),
    ]


class ScheduleConstraintAnonymizer(Anonymizer):

    model = ScheduleConstraint

    attributes = [
        ('id', "SKIP"),
        ('program_id', "SKIP"),
        ('condition_id', "SKIP"),
        ('requirement_id', "SKIP"),
        ('on_failure', "lorem"),
    ]


class ScheduleTestTimeblockAnonymizer(Anonymizer):

    model = ScheduleTestTimeblock

    attributes = [
        ('id', "SKIP"),
        ('booleantoken_ptr_id', "SKIP"),
        ('exp_id', "SKIP"),
        ('text', "lorem"),
        ('seq', "integer"),
        ('timeblock_id', "SKIP"),
    ]


class ScheduleTestOccupiedAnonymizer(Anonymizer):

    model = ScheduleTestOccupied

    attributes = [
        ('id', "SKIP"),
        ('booleantoken_ptr_id', "SKIP"),
        ('scheduletesttimeblock_ptr_id', "SKIP"),
        ('exp_id', "SKIP"),
        ('text', "lorem"),
        ('seq', "integer"),
        ('timeblock_id', "SKIP"),
    ]


class ScheduleTestCategoryAnonymizer(Anonymizer):

    model = ScheduleTestCategory

    attributes = [
        ('id', "SKIP"),
        ('booleantoken_ptr_id', "SKIP"),
        ('scheduletesttimeblock_ptr_id', "SKIP"),
        ('exp_id', "SKIP"),
        ('text', "lorem"),
        ('seq', "integer"),
        ('timeblock_id', "SKIP"),
        ('category_id', "SKIP"),
    ]


class ScheduleTestSectionListAnonymizer(Anonymizer):

    model = ScheduleTestSectionList

    attributes = [
        ('id', "SKIP"),
        ('booleantoken_ptr_id', "SKIP"),
        ('scheduletesttimeblock_ptr_id', "SKIP"),
        ('exp_id', "SKIP"),
        ('text', "lorem"),
        ('seq', "integer"),
        ('timeblock_id', "SKIP"),
        ('section_ids', "lorem"),
    ]


class VolunteerRequestAnonymizer(Anonymizer):

    model = VolunteerRequest

    attributes = [
        ('id', "SKIP"),
        ('program_id', "SKIP"),
        ('timeslot_id', "SKIP"),
        ('num_volunteers', "positive_integer"),
    ]


class VolunteerOfferAnonymizer(Anonymizer):

    model = VolunteerOffer

    attributes = [
        ('id', "SKIP"),
        ('request_id', "SKIP"),
        ('confirmed', "bool"),
        ('user_id', "SKIP"),
        ('email', "email"),
        ('name', "name"),
        ('phone', "phonenumber"),
        ('shirt_size', "choice"),
        ('shirt_type', "choice"),
        ('comments', "lorem"),
    ]


class RegistrationTypeAnonymizer(Anonymizer):

    model = RegistrationType

    attributes = [
        ('id', "SKIP"),
        ('name', "name"),
        ('displayName', "varchar"),
        ('description', "lorem"),
        ('category', "varchar"),
    ]


class StudentRegistrationAnonymizer(Anonymizer):

    model = StudentRegistration

    attributes = [
        ('id', "SKIP"),
        ('start_date', "datetime"),
        ('end_date', "datetime"),
        ('section_id', "SKIP"),
        ('user_id', "SKIP"),
        ('relationship_id', "SKIP"),
    ]


class StudentSubjectInterestAnonymizer(Anonymizer):

    model = StudentSubjectInterest

    attributes = [
        ('id', "SKIP"),
        ('start_date', "datetime"),
        ('end_date', "datetime"),
        ('subject_id', "SKIP"),
        ('user_id', "SKIP"),
    ]


class ClassSizeRangeAnonymizer(Anonymizer):

    model = ClassSizeRange

    attributes = [
        ('id', "SKIP"),
        ('range_min', "integer"),
        ('range_max', "integer"),
        ('program_id', "SKIP"),
    ]


class ProgramCheckItemAnonymizer(Anonymizer):

    model = ProgramCheckItem

    attributes = [
        ('id', "SKIP"),
        ('program_id', "SKIP"),
        ('title', "varchar"),
        ('seq', "positive_integer"),
    ]


class ClassSectionAnonymizer(Anonymizer):

    model = ClassSection

    attributes = [
        ('id', "SKIP"),
        ('anchor_id', "SKIP"),
        ('status', "integer"),
        ('registration_status', "integer"),
        ('duration', "decimal"),
        ('max_class_capacity', "integer"),
        ('parent_class_id', "SKIP"),
        ('enrolled_students', "integer"),
    ]


class ClassSubjectAnonymizer(Anonymizer):

    model = ClassSubject

    attributes = [
        ('id', "SKIP"),
        ('anchor_id', "SKIP"),
        ('title', "lorem"),
        ('parent_program_id', "SKIP"),
        ('category_id', "SKIP"),
        ('class_info', "lorem"),
        ('allow_lateness', "bool"),
        ('message_for_directors', "lorem"),
        ('class_size_optimal', "integer"),
        ('optimal_class_size_range_id', "SKIP"),
        ('grade_min', "integer"),
        ('grade_max', "integer"),
        ('class_size_min', "integer"),
        ('hardness_rating', "lorem"),
        ('class_size_max', "integer"),
        ('schedule', "lorem"),
        ('prereqs', "lorem"),
        ('requested_special_resources', "lorem"),
        ('directors_notes', "lorem"),
        ('requested_room', "lorem"),
        ('session_count', "integer"),
        ('purchase_requests', "lorem"),
        ('custom_form_data', "lorem"),
        ('status', "integer"),
        ('duration', "decimal"),
    ]


class ClassImplicationAnonymizer(Anonymizer):

    model = ClassImplication

    attributes = [
        ('id', "SKIP"),
        ('cls_id', "SKIP"),
        ('parent_id', "SKIP"),
        ('is_prereq', "bool"),
        ('enforce', "bool"),
        ('member_ids', "varchar"),
        ('operation', "choice"),
    ]


class ClassCategoriesAnonymizer(Anonymizer):

    model = ClassCategories

    attributes = [
        ('id', "SKIP"),
        ('category', "lorem"),
        ('symbol', "varchar"),
        ('seq', "integer"),
    ]


class StudentAppQuestionAnonymizer(Anonymizer):

    model = StudentAppQuestion

    attributes = [
        ('id', "SKIP"),
        ('program_id', "SKIP"),
        ('subject_id', "SKIP"),
        ('question', "lorem"),
        ('directions', "lorem"),
    ]


class StudentAppResponseAnonymizer(Anonymizer):

    model = StudentAppResponse

    attributes = [
        ('id', "SKIP"),
        ('question_id', "SKIP"),
        ('response', "lorem"),
        ('complete', "bool"),
    ]


class StudentAppReviewAnonymizer(Anonymizer):

    model = StudentAppReview

    attributes = [
        ('id', "SKIP"),
        ('reviewer_id', "SKIP"),
        ('date', "datetime"),
        ('score', "choice"),
        ('comments', "lorem"),
        ('reject', "bool"),
    ]


class StudentApplicationAnonymizer(Anonymizer):

    model = StudentApplication

    attributes = [
        ('id', "SKIP"),
        ('program_id', "SKIP"),
        ('user_id', "SKIP"),
        ('done', "bool"),
        ('teacher_score', "positive_integer"),
        ('director_score', "positive_integer"),
        ('rejected', "bool"),
    ]


class ClassFlagTypeAnonymizer(Anonymizer):

    model = ClassFlagType

    attributes = [
        ('id', "SKIP"),
        ('name', "name"),
        ('show_in_scheduler', "bool"),
        ('show_in_dashboard', "bool"),
        ('seq', "small_integer"),
        ('color', "varchar"),
    ]


class ClassFlagAnonymizer(Anonymizer):

    model = ClassFlag

    attributes = [
        ('id', "SKIP"),
        ('subject_id', "SKIP"),
        ('flag_type_id', "SKIP"),
        ('comment', "lorem"),
        ('modified_by_id', "SKIP"),
        ('modified_time', "datetime"),
        ('created_by_id', "SKIP"),
        ('created_time', "datetime"),
    ]
