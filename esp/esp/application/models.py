import logging
logger = logging.getLogger(__name__)

from django.db import models, transaction
from django.apps import apps
from django.template import Template, Context
from django.dispatch import receiver
from argcache import cache_function
from esp.users.models import ESPUser
from esp.program.models import Program, ClassSubject
from esp.formstack.api import Formstack
from esp.formstack.objects import FormstackForm, FormstackSubmission
from esp.formstack.signals import formstack_post_signal

class FormstackAppSettings(models.Model):
    """
    Settings and helper methods for the Formstack student application
    module.
    """

    program = models.OneToOneField(Program)

    # formstack settings
    form_id = models.IntegerField(null=True)
    api_key = models.CharField(max_length=80)
    finaid_form_id = models.IntegerField(null=True, blank=True)
    # end formstack settings

    username_field = models.IntegerField(null=True, blank=True)
    coreclass_fields = models.CommaSeparatedIntegerField(max_length=80, blank=True, help_text="A list of field ids separated by commas.")

    autopopulated_fields = models.TextField(blank=True, help_text="""\
To autopopulate fields on the form, type "[field id]: [Python
expression that returns field value]", one field per line. The Python
expression can use the variable 'user' to refer to request.user.

Caution: expressions will be eval()'d by the server.""")

    finaid_user_id_field = models.IntegerField(null=True, blank=True)
    finaid_username_field = models.IntegerField(null=True, blank=True)

    teacher_view_template = models.TextField(blank=True, help_text="""\
An HTML template for what teachers see when they view an app. To
include the content of a field, use {{field.12345}} where 12345 is the
field id.""")

    app_is_open = models.BooleanField(default=False, verbose_name="Application is currently open")

    @property
    def module(self):
        """Deprecated; you probably shouldn't need this."""
        # TODO(benkraft): remove.
        return self.program.getModule('FormstackAppModule')

    def formstack(self):
        """
        A reference to the Formstack client using the stored API key.
        """
        return Formstack(self.api_key)

    def form(self):
        if self.form_id is not None:
            return FormstackForm(self.form_id, self.formstack())
        return None

    def finaid_form(self):
        if self.finaid_form_id is not None:
            return FormstackForm(self.finaid_form_id, self.formstack())
        return None

    def create_username_field(self):
        """
        Creates a form field for ESP Username, returns the field ID,
        and sets the username_field attribute on this object.
        """
        # create a new read-only field
        api_response = self.formstack().create_field(self.form_id, {
                'field_type': 'text',
                'label': 'ESP Username',
                'required': 1,
                'readonly': 1,
                'sort': 1 # puts it at the top of the form
                })
        self.username_field = api_response['id']
        self.save()

class StudentProgramApp(models.Model):
    """ A student's application to the program. """

    user = models.ForeignKey(ESPUser)
    program = models.ForeignKey(Program)

    # choices for admin status
    UNREVIEWED = 0
    APPROVED = 1
    REJECTED = -1
    admin_status = models.IntegerField(default=UNREVIEWED, choices=[
            (UNREVIEWED, 'Unreviewed'),
            (APPROVED, 'Approved'),
            (REJECTED, 'Rejected'),
            ])

    admin_comment = models.TextField(blank=True)

    app_type = models.CharField(max_length=80, choices=[
            ('Formstack', 'Formstack'),
            ])

    # formstack
    submission_id = models.IntegerField(null=True, unique=True)

    def __unicode__(self):
        return "{}'s app for {}".format(self.user, self.program)

    def __init__(self, *args, **kwargs):
        super(StudentProgramApp, self).__init__(*args, **kwargs)

        if self.__class__ == StudentProgramApp:
            model = apps.get_model('application', self.app_type + self.__class__.__name__)
            if model is not None:
                self.__class__ = model

    def choices(self):
        """
        Returns a dict: preference -> subject, of all the class choices
        tied to this app.
        """
        choices = {}
        for classapp in self.studentclassapp_set.all():
            choices[classapp.student_preference] = classapp.subject
        return choices

    def admitted_to_class(self):
        """
        Returns the ClassSubject this student was accepted to, or None.
        """
        classapps = self.studentclassapp_set.filter(admission_status=StudentClassApp.ADMITTED)
        if classapps.exists():
            assert classapps.count() == 1
            return classapps[0].subject
        else:
            return None

    def waitlisted_to_class(self):
        """
        Returns the ClassSubject(s) this student was waitlisted to.
        """
        result = []
        classapps = self.studentclassapp_set.filter(admission_status=StudentClassApp.WAITLIST)
        for classapp in classapps:
            result.append(classapp.subject)
        return result

class StudentClassApp(models.Model):
    """ A student's application to a particular class. """

    app = models.ForeignKey(StudentProgramApp)
    subject = models.ForeignKey(ClassSubject)
    student_preference = models.PositiveIntegerField()

    GREEN = 1
    YELLOW = 2
    RED = 3
    teacher_rating = models.PositiveIntegerField(null=True, blank=True, choices=[
            (GREEN, 'Green'),
            (YELLOW, 'Yellow'),
            (RED, 'Red'),
            ])
    teacher_ranking = models.PositiveIntegerField(null=True, blank=True)
    teacher_comment = models.TextField(blank=True)

    UNASSIGNED = 0
    ADMITTED = 1
    WAITLIST = 2
    admission_status = models.IntegerField(default=UNASSIGNED, choices=[
            (UNASSIGNED, 'Unassigned'),
            (ADMITTED, 'Admitted'),
            (WAITLIST, 'Waitlist'),
            ])

    def __unicode__(self):
        return "{}'s app for {}".format(self.app.user, self.subject)

    def __init__(self, *args, **kwargs):
        super(StudentClassApp, self).__init__(*args, **kwargs)

        if self.__class__ == StudentClassApp:
            model = apps.get_model('application', self.app.app_type + self.__class__.__name__)
            if model is not None:
                self.__class__ = model

    def admit(self):
        # note: this will un-admit the student from all other classes
        for classapp in self.app.studentclassapp_set.all():
            classapp.admission_status = self.UNASSIGNED
            classapp.save()
        self.admission_status = self.ADMITTED
        self.save()

    def unadmit(self):
        self.admission_status = self.UNASSIGNED
        self.save()

    def waitlist(self):
        self.admission_status = self.WAITLIST
        self.save()

    class Meta:
        unique_together = (('app', 'student_preference'),)

class FormstackStudentProgramAppManager(models.Manager):
    def create_from_submission(self, submission, settings):
        """ Takes a FormstackSubmission and creates an app from it. """
        program = settings.program
        data_dict = { int(entry['field']): entry['value']
                      for entry in submission.data() }

        # link user
        username = data_dict.get(settings.username_field)
        try:
            user = ESPUser.objects.get(username=username)
        except ESPUser.DoesNotExist:
            raise LookupError("no matching user {0}".format(username))

        # define mapping from string to class subject
        def get_subject(s):
            if s is None: return None
            val = s.split('|')[0]
            try:
                cls_id = int(val)
                cls = program.classes().get(id=cls_id)
                return cls
            except ClassSubject.DoesNotExist:
                return None
            except ValueError:
                cls_title = val.strip()
                clses = program.classes().filter(title=cls_title)
                if clses:
                    return clses[0]
                else:
                    return None

        # link class subjects
        choices = {}
        for index, field in enumerate(settings.coreclass_fields.split(',')):
            value = data_dict.get(int(field))
            choices[index + 1] = get_subject(value)

        # update app object, or make one if it doesn't exist
        try:
            app = self.get(submission_id=submission.id)
        except self.model.DoesNotExist:
            app = self.model(submission_id=submission.id)
        app.user = user
        app.program = program
        app.save()

        # update class app objects
        for preference, subject in choices.items():
            if subject is not None:
                try:
                    classapp = FormstackStudentClassApp.objects.get(app=app, student_preference=preference)
                except FormstackStudentClassApp.DoesNotExist:
                    classapp = FormstackStudentClassApp(app=app, student_preference=preference)
                classapp.subject = subject
                classapp.save()

        return app

    def fetch(self, program):
        """ Get apps for a particular program from the Formstack API. """

        # get submissions from the API
        settings = program.formstackappsettings
        submissions = settings.form().submissions(use_cache=False)

        # parse submitted data and make model instances
        with transaction.atomic():
            apps = []
            for submission in submissions:
                try:
                    app = self.create_from_submission(submission, settings)
                    apps.append(app)
                except Exception as e:
                    logger.exception("Failed to get submissions: %s", e)

        return apps

@receiver(formstack_post_signal)
def create_app(sender, form_id, submission_id, fields, **kwargs):
    """ Called whenever a Formstack form is submitted. """

    data = [{'field': field, 'value': value}
            for field, value in fields.items()]
    for settings in FormstackAppSettings.objects.filter(form_id=form_id):
        submission = FormstackSubmission(submission_id, settings.formstack())
        submission.data.set([submission], data) # set data cache
        FormstackStudentProgramApp.objects.create_from_submission(submission, settings)

class FormstackStudentProgramApp(StudentProgramApp):
    """ A student's application through Formstack. """

    objects = FormstackStudentProgramAppManager()

    def __init__(self, *args, **kwargs):
        super(FormstackStudentProgramApp, self).__init__(*args, **kwargs)
        self.app_type = 'Formstack'

    def program_settings(self):
        return self.program.formstackappsettings

    def submission(self):
        return FormstackSubmission(self.submission_id, self.program_settings().formstack())

    def get_responses(self, program=None):
        """ Returns a list of (question, response) tuples from submitted data. """

        if program and program == self.program:
            self.program = program # optimization: if we're calling this a lot, passing in the same program object lets us save results
        data = self.submission().data()
        field_info = self.program_settings().form().field_info()
        id_to_label = { field['id']: field['label'] for field in field_info }
        result = []
        for response in data:
            result.append((id_to_label[response['field']],
                           response['value']))
        return result

    def get_teacher_view(self, program=None):
        """ Renders a "teacher view" for an app using a configurable template. """

        if program and program == self.program:
            self.program = program # optimization: if we're calling this a lot, passing in the same program object lets us save results
        data = self.submission().data()
        data_dict = {}
        for response in data:
            data_dict[response['field']] = response['value']
        template = Template(self.program_settings().teacher_view_template)
        context = Context({'field': data_dict})
        return template.render(context)

    class Meta:
        proxy = True

class FormstackStudentClassApp(StudentClassApp):
    """ A student's application to a class through Formstack. """

    def get_responses(self, prog=None):
        return self.app.get_responses(prog)

    def get_teacher_view(self, prog=None):
        return self.app.get_teacher_view(prog)

    class Meta:
        proxy = True
