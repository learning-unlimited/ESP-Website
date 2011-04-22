import datetime
import random

from twill.commands import *
from generators import *

base_host = 'http://dev2.learningu.org'
splash_name = 'Splash/2011_Spring'

people_generator = random_people('Teacher')



def register_users():
    for i in range(200):
        register_user(people_generator.next())

def register_user(user):
    b = get_browser()
    b.go('%s/myesp/signout' % base_host)
    b.go('%s/myesp/register' % base_host)
    fv("3", "first_name", user.first)
    fv("3", "last_name", user.last)
    fv("3", "password", "testtest")
    fv("3", "username", user.username)
    fv("3", "confirm_password", "testtest")
    fv("3", "initial_role", user.user_type)
    fv("3", "email", user.email)
    submit('0')

    if user.user_type == 'Student':
        register_student_profile(b, user)
    elif user.user_type == 'Teacher':
        register_teacher_profile(b, user)
        for i in range(random.randint(0, 5)):
            register_teacher_splash(b, user)
    return b


def register_student_profile(b, user):
    parent = people_generator.next()
    address = random_address().next()
    emerg = people_generator.next()
    emerg_address = random_address().next()
    phone = random_phone().next()
    update_info = {
        'address_street': address.street,
        'address_city': address.city,
        'address_state': address.state,
        'address_zip': address.zip,
        'phone_day': phone,
        'phone_cell': phone,
        'dob_0': user.dob.month,
        'dob_1': user.dob.day,
        'dob_2': user.dob.year,
        'graduation_year': datetime.date.today().year - user.grade + 12,
        'k12school': "Test school",
        "guard_first_name": parent.first,
        "guard_last_name": parent.last,
        "guard_e_mail": parent.email,
        "guard_phone_day": random_phone().next(),
        "guard_phone_cell": random_phone().next(),
        "emerg_first_name": emerg.first,
        "emerg_last_name": emerg.last,
        "emerg_e_mail": emerg.email,
        "emerg_address_street": emerg_address.street,
        "emerg_address_city": emerg_address.city,
        "emerg_address_state": emerg_address.state,
        "emerg_address_zip": emerg_address.zip,
        "emerg_phone_day": random_phone().next(),
        "emerg_phone_cell": random_phone().next(),
        }
    for key, value in update_info.items():
        try:
            fv('2', key, str(value))
        except TwillException:
            pass
    submit('0')

def register_teacher_profile(b, user):
    address = random_address().next()
    phone = random_phone().next()
    cell = random_phone().next()
    update_info = {
        'address_street': address.street,
        'address_city': address.city,
        'address_state': address.state,
        'address_zip': address.zip,
        'phone_day': phone,
        'from_here': 'True',
        'graduation_year': datetime.date.today().year - user.grade + 12,
        'major': "Software Testing",
        }
    for key, value in update_info.items():
        try:
            fv('2', key, str(value))
        except TwillException:
            pass
    submit('0')

def register_teacher_splash(b, user):
    b.go('%s/teach/%s/makeaclass' % (base_host, splash_name))
    class_ = random_classes().next()
    update_info = {
        'title': class_.title,
        'class_info': class_.description,
        'grade_min': class_.min_grade,
        'grade_max': class_.max_grade,
        }

    for control in b.get_form(2).controls:
        if control and control.type == 'select' and control.name not in update_info:
            item_values = []
            for item in control.items:
                try:
                    if item.name.strip():
                        item_values.append(item.name)
                except AttributeError, ValueError:
                    pass
            if item_values:
                update_info[control.name] = random.choice(item_values)
    for key, value in update_info.items():
        fv('2', key, str(value))
    b.submit()


if __name__ == '__main__':
    register_users()
