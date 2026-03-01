"""
WARNING!
This code contains utilities to populate the database with FAKE data (names, addresses, phone numbers, etc.).
It is to be used on development servers, NOT production servers!
In production, if you want to bulk create a large number of blank accounts for use by students or teachers, use
 the UI in the Bulk Create Accounts module.

These utilities should be useful for general testing during development, and could also be used for performance
testing by populating a large number of accounts.

You will need to install the faker library (used to generate fake data) on your dev server:
  pip install faker

To use these utilities, one way is to launch the Django shell from the root directory of your dev server with:
   esp/esp/manage.py shell_plus
then read in these utilities with
   exec(open("esp/useful_scripts/generate_bulk_fake_data.py").read())
Then you can call these functions within the shell.

The functions available are below. See the documentation within the code. Please update this list if you add
a function.

generate_user(role, group, program=None)
generate_k12school()
generate_student_info(student, min_grade, max_grade, schools)
fill_teacher_availability(teachers, program)
enroll_student_in_section(student, class_section)
remove_student_from_section(student, class_section)
"""

from datetime import datetime
from esp.users.models import ESPUser, ContactInfo, K12School, StudentInfo
from esp.users.forms.user_profile import HEARD_ABOUT_ESP_CHOICES
from esp.program.models import RegistrationProfile
from django.contrib.auth.models import Group
from faker import Faker
from phonenumber_field.phonenumber import PhoneNumber
import random

fake = Faker()

def try_get_phone():
    phone = ''
    # generate a 555 number, because it's never a real phone number, but is accepted by Django's phone number validator
    # https://en.wikipedia.org/wiki/Fictitious_telephone_number
    for i in range(10):
        if i not in [3, 4, 5]:
            phone += str(random.randint(0, 9))
        else:
            phone += '5'
    return phone

def get_clean_phone():
    phone = try_get_phone()
    while not PhoneNumber.from_string(phone).is_valid():
        phone = try_get_phone()
    return phone

def generate_user(role, group, program=None):
    """
    Generates a random user with their contact information randomly filled out, and optionally attaches the profile to a program.
    This doesn't fill out the `StudentInfo` or `TeacherInfo`.  See `generate_student_info` to generate a random student info and
    attach it to a student.  (There is no `generate_teacher_info` yet.)

    `role`: string, either`Student` or `Teacher`
    `group`: string, a group name (besides `Student` or `Teacher`) to put this user into. This is useful for finding these users
             after you created them.
    `program`: `Program`, the program to put this registration profile into (if any)
    """

    if role not in ['Student', 'Teacher']:
        raise ValueError("Only Student and Teacher roles are supported.")

    # basic User information
    username = fake.user_name()
    while ESPUser.objects.filter(username=username).exists():
        username = fake.user_name()
    email = fake.email()
    password = username

    user = ESPUser.objects.create_user(username, email, password)
    user.last_name = fake.last_name()
    user.first_name = fake.first_name()
    user.set_password(password)
    role_group = Group.objects.get(name=role)
    other_group = Group.objects.get_or_create(name=group)[0]
    user.groups.add(role_group, other_group)
    user.save()

    # user contact info
    phone_day = get_clean_phone()
    street = fake.address().split('\n')[0]
    city = fake.city()
    state = fake.state_abbr()
    zip = fake.zipcode_in_state(state)
    contact_info = ContactInfo.objects.create(
        user=user,
        first_name=user.first_name,
        last_name=user.last_name,
        e_mail=user.email,
        phone_day=phone_day,
        address_street=street,
        address_city=city,
        address_state=state,
        address_zip=zip,
        address_country='US'
    )

    if role == 'Student':
        # registration profile
        guardian_email = fake.email()
        guardian_first_name = fake.first_name()
        guardian_phone = get_clean_phone()
        contact_guardian = ContactInfo.objects.create(
            user=user,
            first_name=guardian_first_name,
            last_name=user.last_name,
            e_mail=guardian_email,
            phone_day=guardian_phone,
            address_street=street,
            address_city=city,
            address_state=state,
            address_zip=zip,
            address_country='US'
        )

        RegistrationProfile.objects.create(
            user=user,
            program=program,
            contact_user=contact_info,
            contact_guardian=contact_guardian,
            contact_emergency=contact_guardian
        )
    elif role == 'Teacher':
        RegistrationProfile.objects.create(
            user=user,
            program=program,
            contact_user=contact_info,
        )

    return user

def generate_k12school():
    """
    Generates a random `K12School`. You need at least one of these before calling `generate_student_info`.
    """

    name = ' '.join(fake.text().split(' ',3)[:3])
    k12school = K12School.objects.create(
        name=name
    )
    return k12school

def generate_student_info(student, min_grade, max_grade, schools):
    """
    Generate a random StudentInfo with grade between min_grade and max_grade, and k12school randomly chosen among `schools`,
    and attaches it to the student's last registration profile.

    student: the ESPUser that this StudentInfo should be attached to
    min_grade: the minimum grade to select
    max_grade: the maximum grade to select
    schools: The list of `K12School` that we should choose from (uniformly randomly). You can simulate a different distribution
             by repeating some schools multiple times. Use `generate_k12school` to generate a random school.
    """

    student_info = StudentInfo()
    student_info.user = student

    # generate a random grade according to the distribution
    grade = random.randint(min_grade, max_grade)
    student_info.graduation_year = ESPUser.YOGFromGrade(grade)

    # generate a random K12School
    random_school_index = random.randint(0, len(schools)-1)
    student_info.k12school = schools[random_school_index]

    # generate a random date of birth based on the grade
    year_of_birth = student_info.graduation_year - 18
    month_of_birth = random.randint(1, 12)

    # https://en.wikipedia.org/wiki/Thirty_Days_Hath_September
    day_of_birth = random.randint(1,
                                  30 if month_of_birth in [4, 6, 9, 11] else  # Thirty days hath September / April, June, and November
                                  28 if month_of_birth == 2 and year_of_birth % 4 != 0 else  # Save February at twenty-eight
                                  29 if month_of_birth == 2 else  # But leap year, coming once in four / February then has one day more
                                  31  # All the rest have thirty-one
                                 )

    student_info.dob = datetime(year_of_birth, month_of_birth, day_of_birth)

    # generate random "heard about"
    random_heardabout_index = random.randint(1, len(HEARD_ABOUT_ESP_CHOICES)-1)  # skip blank
    student_info.heard_about = HEARD_ABOUT_ESP_CHOICES[random_heardabout_index] + ':'
    if random_heardabout_index == 1:  # Other...
        student_info.heard_about += fake.text().split('\n')[0].split('.')[0]  # random "sentence"

    student_info.save()

    # Attach student info to the student's last profile
    last_profile = student.getLastProfile()
    last_profile.student_info = student_info
    last_profile.save()

    return student_info

def fill_teacher_availability(teachers, program):
    """
    Fill full availability for all teachers in the program
    """
    if not program:
        raise ValueError("Must pass in a valid program")
    timeslots = program.getTimeSlots()
    for teacher in teachers:
        for timeslot in timeslots:
            teacher.addAvailableTime(program, timeslot)

def enroll_student_in_section(student, class_section):
    """
    Enrolls a `Student` into a `ClassSection`.
    """

    class_section.preregister_student(student, overridefull=True)

def remove_student_from_section(student, class_section):
    """
    Remove a `Student` from a `ClassSection`.
    """

    class_section.unpreregister_student(student)
