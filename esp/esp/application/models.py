from django.db import models
from django.template import Template, Context
from django.core.exceptions import ObjectDoesNotExist
from esp.users.models import ESPUser
from esp.program.models import Program, ClassSubject
from esp.program.modules.base import ProgramModuleObj
from esp.formstack.api import Formstack
from esp.formstack.models import FormstackForm
from esp.lib.markdown import markdown

class FormstackAppSettings(models.Model):
    """
    Settings and helper methods for the Formstack student application
    module.
    """

    module = models.ForeignKey(ProgramModuleObj)

    # formstack settings
    form = models.ForeignKey(FormstackForm, null=True)
    api_key = models.CharField(max_length=80)
    handshake_key = models.CharField(max_length=80)
    # end formstack settings

    username_field = models.IntegerField(null=True)
    coreclass1_field = models.IntegerField(null=True)
    coreclass2_field = models.IntegerField(null=True)
    coreclass3_field = models.IntegerField(null=True)

    teacher_view_template = models.TextField()

    @property
    def formstack(self):
        """
        A reference to the Formstack client using the stored API key.
        """
        return Formstack(self.api_key)

    def get_program(self):
        """
        Helper function that returns the program associated with this
        object, whether you're calling from this class or a module
        inheriting it.
        """
        if isinstance(self, ProgramModuleObj):
            return self.program
        elif isinstance(self.module, ProgramModuleObj):
            return self.module.program
        else:
            return None

    def create_username_field(self):
        """
        Creates a form field for ESP Username, returns the field ID,
        and sets the username_field attribute on this object.

        Does not save to the database; you must call .save() yourself.
        """
        # create a new read-only field
        api_response = self.formstack.create_field(self.form_id, {
                'field_type': 'text',
                'label': 'ESP Username',
                'required': 1,
                'readonly': 1,
                'sort': 1 # puts it at the top of the form
                })
        self.username_field = api_response['id']

    def get_field_info(self):
        """
        Returns a list of JSON dicts, one per form field, containing
        metadata (e.g. field name).
        """

        # return cached copy if available
        if hasattr(self, '_fields'):
            return self._fields
        # get info from the API
        api_response = self.formstack.form(self.form.id)
        fields = api_response['fields']
        # save cached copy
        self._fields = fields
        return fields

    def get_student_apps(self):
        """
        Returns a list of StudentApp objects, one per valid form submission.
        """

        # return cached copy if available
        if hasattr(self, '_apps'):
            return self._apps

        # fetch and store if unavailable
        apps = FormstackStudentApp.objects.fetch(self.get_program())
        self._apps = apps
        return apps

class StudentProgramApp(models.Model):
    """ A student's application to the program. """

    user = models.ForeignKey(ESPUser)
    program = models.ForeignKey(Program)

    # choices for admin status
    UNREVIEWED = 0
    APPROVED = 1
    ADMITTED = 2
    REJECTED = 3
    WAITLIST = 4
    admin_status = models.IntegerField(default=UNREVIEWED, choices=[
            (UNREVIEWED, 'Unreviewed'),
            (APPROVED, 'Approved'),
            (ADMITTED, 'Admitted'),
            (REJECTED, 'Rejected'),
            (WAITLIST, 'Waitlist')
            ])

    admin_comment = models.TextField()

    def __unicode__(self):
        return "{}'s app for {}".format(self.user, self.program)

    def choices(self):
        """
        Returns a dict: preference -> subject, of all the class choices
        tied to this app.
        """
        choices = {}
        for classapp in self.studentclassapp_set.all():
            choices[classapp.student_preference] = classapp.subject
        return choices

class StudentClassApp(models.Model):
    """ A student's application to a particular class. """

    app = models.ForeignKey(StudentProgramApp)
    subject = models.ForeignKey(ClassSubject)
    student_preference = models.PositiveIntegerField()

    teacher_rating = models.PositiveIntegerField(null=True)
    teacher_comment = models.TextField()

    def __unicode__(self):
        return "{}'s app for {}".format(self.app.user, self.subject)

    class Meta:
        unique_together = (('app', 'student_preference'),)

class FormstackStudentAppManager(models.Manager):
    fetched = set()
    def fetch(self, program):
        """ Get apps for a particular program from the Formstack API. """
        self.fetched.add(program)
        # get submissions from the API
        settings = program.getModuleExtension('FormstackAppSettings')
        api_response = settings.formstack.data(settings.form.id, {'per_page': 100})
        submissions = api_response['submissions']
        for i in range(1, api_response['pages']):
            api_response = settings.formstack.data(settings.form.id,
                                               {'per_page': 100, 'page': i+1})
            submissions += api_response['submissions']
        # parse submissions, link usernames, make a StudentApp object
        apps = []
        for submission in submissions:
            submission_id = int(submission['id'])
            data_dict = { int(entry['field']): entry['value']
                          for entry in submission['data'] }
            username = data_dict.get(settings.username_field)
            try:
                user = ESPUser.objects.get(username=username)
            except ObjectDoesNotExist:
                continue # no matching user, ignore

            def get_subject(title):
                if title is None: return None
                return program.classes().get(anchor__friendly_name=title)

            choices = {}
            choices[1] = get_subject(data_dict.get(settings.coreclass1_field))
            choices[2] = get_subject(data_dict.get(settings.coreclass2_field))
            choices[3] = get_subject(data_dict.get(settings.coreclass3_field))
            app, created = self.get_or_create(
                submission_id=submission_id,
                defaults={
                    'user': user,
                    'program': program
                    })
            for preference, subject in choices.items():
                if subject is not None:
                    StudentClassApp.objects.get_or_create(
                        app=app,
                        student_preference=preference,
                        defaults={
                            'subject': subject
                            })
            app._data = submission # cache submitted data
            apps.append(app)
        # remove obsolete model instances (deleted from Formstack?)
        all_apps = self.filter(program=program)
        old_apps = all_apps.exclude(id__in=[app.id for app in apps])
        old_apps.delete()
        return apps

    def get_query_set(self):
        for program in Program.objects.filter(program_modules__handler='FormstackAppModule'):
            if program not in self.fetched:
                self.fetch(program)
        return super(FormstackStudentAppManager, self).get_query_set()

class FormstackStudentApp(StudentProgramApp):
    """ A student's application through Formstack. """

    submission_id = models.IntegerField(unique=True)
    objects = FormstackStudentAppManager()

    @property
    def program_settings(self):
        return self.program.getModuleExtension('FormstackAppSettings')

    def get_submitted_data(self):
        """ Returns the raw submitted data from the API, as a JSON dict. """

        # return cached copy if available
        if hasattr(self, '_data'):
            return self._data

        submission = self.program_settings.formstack.submission(self.submission_id)
        self._data = submission
        return submission

    def get_responses(self):
        """ Returns a list of (question, response) tuples from submitted data. """

        data = self.get_submitted_data()
        info = self.program_settings.get_field_info()
        id_to_label = { field['id']: field['label'] for field in info }
        result = []
        for response in data['data']:
            result.append((id_to_label[response['field']],
                           response['value']))
        return result

    def get_teacher_view(self):
        """ Renders a "teacher view" for an app using a configurable template. """

        data = self.get_submitted_data()
        data_dict = {}
        for response in data['data']:
            data_dict[response['field']] = response['value']
        template = Template(self.program_settings.teacher_view_template)
        context = Context({'fields': data_dict})
        return markdown(template.render(context))
