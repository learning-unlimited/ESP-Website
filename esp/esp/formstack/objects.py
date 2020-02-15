"""
A somewhat higher-level interface to the Formstack API.

Employs caching to avoid hitting Formstack's API more than necessary.
"""

from argcache import cache_function
from esp.formstack.api import Formstack

CACHE_TIMEOUT = 3600 # seconds to keep things cached

def get_forms_for_api_key(api_key):
    """ Shortcut function that returns a list of FormstackForms associated with an API key. """
    return FormstackForm.for_api_key(Formstack(api_key))

def get_form_by_id(form_id, api_key):
    """ Shortcut function that returns a FormstackForm from a form ID. """
    return FormstackForm(form_id, Formstack(api_key))

class FormstackForm(object):
    """
    A Formstack form.
    """

    def __init__(self, form_id, formstack=None):
        self.id = form_id
        self.name = None
        self.formstack = formstack

    @classmethod
    def for_api_key(cls, formstack):
        """ Returns a list of FormstackForms associated with an account. """
        api_response = formstack.forms()
        forms = []
        for form_doc in api_response['forms']:
            form = cls(form_doc['id'])
            form.name = form_doc['name']
            form.formstack = formstack
            form.info.set([form], form_doc)
            forms.append(form)
        return forms

    def __unicode__(self):
        return u'{0}'.format(self.id)

    def __repr__(self):
        return u'<FormstackForm: {0}>'.format(self)

    @cache_function
    def info(self):
        """
        Returns metadata for the form, as a JSON dict.
        """
        api_response = self.formstack.form(self.id)
        fields = api_response.pop('fields')
        self.field_info.set([self], fields)
        return api_response
    info.timeout_seconds = CACHE_TIMEOUT

    @cache_function
    def field_info(self):
        """
        Returns a list of JSON dicts, one per form field, containing
        metadata for each field.
        """
        api_response = self.formstack.form(self.id)
        fields = api_response.pop('fields')
        self.info.set([self], api_response)
        return fields
    field_info.timeout_seconds = CACHE_TIMEOUT

    @cache_function
    def submissions(self):
        """
        Returns a list of FormstackSubmission objects, one for each form submission.
        """
        # get submissions from the API
        api_response = self.formstack.data(self.id, {'per_page': 100})
        submission_docs = api_response['submissions']
        for i in range(1, api_response['pages']):
            api_response = self.formstack.data(self.id,
                                               {'per_page': 100, 'page': i+1})
            submission_docs += api_response['submissions']

        # make FormstackSubmission objects
        submissions = []
        for submission_doc in submission_docs:
            submission = FormstackSubmission(submission_doc['id'])
            submission.data.set([submission], submission_doc['data'])
            submission.formstack = self.formstack
            submissions.append(submission)
        return submissions
    submissions.timeout_seconds = CACHE_TIMEOUT

class FormstackSubmission(object):
    """
    A Formstack form submission.
    """

    def __init__(self, submission_id, formstack=None):
        self.id = submission_id
        self.formstack = formstack

    def __unicode__(self):
        return unicode(self.id)

    def __repr__(self):
        return u'<FormstackSubmission: {0}>'.format(self)

    @cache_function
    def data(self):
        """
        Returns the raw submitted data as a JSON dict.
        """
        api_response = self.formstack.submission(self.id)
        return api_response['data']
    data.timeout_seconds = CACHE_TIMEOUT
