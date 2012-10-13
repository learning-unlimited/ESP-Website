from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from esp.users.models import ESPUser
from esp.program.models import Program
from esp.program.modules.base import ProgramModuleObj
from esp.formstack.api import Formstack
from esp.formstack.models import FormstackForm


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

    @property
    def formstack(self):
        """
        A reference to the Formstack client using the stored API key.
        """
        return Formstack(self.api_key)

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

    def get_student_apps(self, save=True):
        """
        Returns a list of StudentApp objects, one per valid form submission.
        """

        # return cached copy if available
        if hasattr(self, '_apps'):
            return self._apps

        # fetch and store if unavailable
        apps = self.fetch_student_apps(save)
        self._apps = apps
        return apps

    def fetch_student_apps(self, save=True):
        # get submissions from the API
        api_response = self.formstack.data(self.form.id, {'per_page': 100})
        submissions = api_response['submissions']
        for i in range(1, api_response['pages']):
            api_response = self.formstack.data(self.form.id,
                                               {'per_page': 100, 'page': i+1})
            submissions += api_response['submissions']
        # parse submissions, link usernames, make a StudentApp object
        apps = []
        for submission in submissions:
            submission_id = int(submission['id'])
            data_dict = { int(entry['field']): entry['value']
                          for entry in submission['data'] }
            username = data_dict.get(self.username_field)
            try:
                user = ESPUser.objects.get(username=username)
            except ObjectDoesNotExist:
                continue # no matching user, ignore
            coreclass1 = data_dict.get(self.coreclass1_field, '')
            coreclass2 = data_dict.get(self.coreclass2_field, '')
            coreclass3 = data_dict.get(self.coreclass3_field, '')
            if FsStudentApp.objects.filter(id=submission_id).exists():
                app = FsStudentApp.objects.get(id=submission_id)
            else:
                app = FsStudentApp(id=submission_id)
            app.user = user
            app.program = self.module.program
            app.coreclass1 = coreclass1
            app.coreclass2 = coreclass2
            app.coreclass3 = coreclass3
            app._data = submission # cache submitted data
            apps.append(app)
            if save:
                app.save()
        return apps

class FsStudentApp(models.Model):
    """ A student's application. """

    id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(ESPUser)
    program = models.ForeignKey(Program)
    coreclass1 = models.CharField(max_length=80)
    coreclass2 = models.CharField(max_length=80)
    coreclass3 = models.CharField(max_length=80)

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

    def get_submitted_data(self):
        """ Returns the raw submitted data from the API, as a JSON dict. """

        # return cached copy if available
        if hasattr(self, '_data'):
            return self._data

        fsas = self.program.getModuleExtension('FormstackAppSettings')
        submission = fsas.formstack.submission(self.id)
        self._data = submission
        return submission

    def get_responses(self):
        """ Returns a list of (question, response) tuples from submitted data. """

        data = self.get_submitted_data()
        fsas = self.program.getModuleExtension('FormstackAppSettings')
        info = fsas.get_field_info()
        id_to_label = { field['id']: field['label'] for field in info }
        result = []
        for response in data['data']:
            result.append((id_to_label[response['field']],
                           response['value']))
        return result
