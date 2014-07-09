from esp.users.models import UserAvailability, ESPUser, StudentInfo, TeacherInfo, GuardianInfo, EducatorInfo, ZipCode, ZipCodeSearches, ContactInfo, K12School, PersistentQueryFilter, ESPUser_Profile, PasswordRecoveryTicket, EmailPref, Record, Permission, GradeChangeRequest, UserBit, UserBitImplication, UserForwarder
from anonymizer import Anonymizer


class ESPUserAnonymizer(Anonymizer):

    model = ESPUser

    attributes = [
        ('id', "SKIP"),
        ('username', "username"),
        ('first_name', "first_name"),
        ('last_name', "last_name"),
        ('email', "email"),
        ('password', "varchar"),
        ('is_staff', "bool"),
        ('is_active', "bool"),
        ('is_superuser', "bool"),
        ('last_login', "datetime"),
        ('date_joined', "datetime"),
    ]


class StudentInfoAnonymizer(Anonymizer):

    model = StudentInfo

    attributes = [
        ('id', "SKIP"),
        ('user_id', "SKIP"),
        ('graduation_year', "positive_integer"),
        ('k12school_id', "SKIP"),
        ('school', "varchar"),
        ('dob', "date"),
        ('gender', "varchar"),
        ('studentrep', "bool"),
        ('studentrep_expl', "lorem"),
        ('heard_about', "lorem"),
        ('food_preference', "varchar"),
        ('shirt_size', "choice"),
        ('shirt_type', "choice"),
        ('medical_needs', "lorem"),
        ('schoolsystem_id', "varchar"),
        ('schoolsystem_optout', "bool"),
        ('post_hs', "lorem"),
        ('transportation', "lorem"),
    ]


class TeacherInfoAnonymizer(Anonymizer):

    model = TeacherInfo

    attributes = [
        ('id', "SKIP"),
        ('user_id', "SKIP"),
        ('graduation_year', "varchar"),
        ('from_here', "bool"),
        ('is_graduate_student', "bool"),
        ('college', "varchar"),
        ('major', "varchar"),
        ('bio', "lorem"),
        ('shirt_size', "choice"),
        ('shirt_type', "choice"),
        ('full_legal_name', "name"),
        ('university_email', "email"),
        ('student_id', "varchar"),
        ('mail_reimbursement', "bool"),
    ]


class GuardianInfoAnonymizer(Anonymizer):

    model = GuardianInfo

    attributes = [
        ('id', "SKIP"),
        ('user_id', "SKIP"),
        ('year_finished', "positive_integer"),
        ('num_kids', "positive_integer"),
    ]


class EducatorInfoAnonymizer(Anonymizer):

    model = EducatorInfo

    attributes = [
        ('id', "SKIP"),
        ('user_id', "SKIP"),
        ('subject_taught', "varchar"),
        ('grades_taught', "varchar"),
        ('school', "varchar"),
        ('position', "varchar"),
        ('k12school_id', "SKIP"),
    ]





class EmailPrefAnonymizer(Anonymizer):

    model = EmailPref

    attributes = [
        ('id', "SKIP"),
        ('email', "email"),
        ('email_opt_in', "bool"),
        ('first_name', "first_name"),
        ('last_name', "last_name"),
        ('sms_number', "varchar"),
        ('sms_opt_in', "bool"),
    ]



