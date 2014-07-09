from esp.shortterm.models import AdLogEntry, VolunteerRegistration, ResponseForm
from anonymizer import Anonymizer

class AdLogEntryAnonymizer(Anonymizer):

    model = AdLogEntry

    attributes = [
        ('id', "SKIP"),
        ('ts', "datetime"),
        ('ipaddr', "varchar"),
        ('agent', "varchar"),
    ]


class VolunteerRegistrationAnonymizer(Anonymizer):

    model = VolunteerRegistration

    attributes = [
        ('id', "SKIP"),
        ('your_name', "name"),
        ('email_address', "email"),
        ('phone_number', "phonenumber"),
        ('availability', "varchar"),
        ('notes', "lorem"),
    ]


class ResponseFormAnonymizer(Anonymizer):

    model = ResponseForm

    attributes = [
        ('id', "SKIP"),
        ('contact_name', "name"),
        ('position', "varchar"),
        ('email', "email"),
        ('school', "varchar"),
        ('mailing_address', "full_address"),
        ('xeroxable_flier_for_summer_hssp', "bool"),
        ('xeroxable_flier_for_junction', "bool"),
        ('catalog_of_all_2007_to_2008_esp_courses', "bool"),
        ('xeroxable_fliers_for_all_2008_to_2009_esp_courses', "bool"),
        ('splash_on_wheels_application', "SKIP"),
        ('bulk_financial_aid_application', "SKIP"),
    ]
