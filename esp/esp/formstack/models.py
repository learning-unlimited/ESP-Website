"""
A somewhat higher-level interface to the Formstack API.

FormstackForm and FormstackSubmission aren't real Django models, but
in some sense the are models -- except that rather than living in our
database they live in Formstack's database.

Employs caching to avoid hitting Formstack's API more than necessary.
"""

from django.core.cache import cache
from esp.formstack.api import Formstack

__all__ = ['get_forms_for_api_key', 'FormstackForm', 'FormstackSubmission']

CACHE_TIMEOUT = 3600 # seconds to keep things cached

def cached_property(key_func):
    """
    Makes a property attribute that gets its value from the cache.

    key_func is a function that takes an object and returns a cache
    key to associate with that object.
    """

    def getter(self):
        return cache.get(key_func(self))
    def setter(self, value):
        return cache.set(key_func(self), value, CACHE_TIMEOUT)
    def deleter(self):
        return cache.delete(key_func(self))

    return property(getter, setter, deleter)

def get_forms_for_api_key(api_key):
    """ Shortcut function that returns a list of FormstackForms associated with an API key. """
    return FormstackForm.for_api_key(Formstack(api_key))

class FormstackForm(object):
    """
    A Formstack form.
    """

    def __init__(self, form_id, formstack=None):
        self.id = form_id
        self.formstack = formstack
        if formstack is not None and self._info_cache is None:
            self.get_info()

    @classmethod
    def for_api_key(cls, formstack):
        """ Returns a list of FormstackForms associated with an account. """
        api_response = formstack.forms()
        forms = []
        for form_doc in api_response['forms']:
            form = cls(form_doc['id'])
            form._info_cache = form_doc
            form.formstack = formstack
            forms.append(form)
        return forms

    def __unicode__(self):
        return self.get_info()['name']

    def __repr__(self):
        return u'<FormstackForm: {0}>'.format(self)

    def _info_cache_key(self):
        return 'formstackform_info_{}'.format(self.id)
    _info_cache = cached_property(_info_cache_key)

    def _fields_cache_key(self):
        return 'formstackform_fields_{}'.format(self.id)
    _fields_cache = cached_property(_fields_cache_key)

    def get_info(self):
        """
        Returns metadata for the form, as a JSON dict.
        """
        # return cached copy if available
        if self._info_cache is not None:
            return self._info_cache

        # get info from the API and save in cache
        api_response = self.formstack.form(self.id)
        fields = api_response.pop('fields')
        self._info_cache = api_response
        self._fields_cache = fields
        return api_response

    def get_field_info(self):
        """
        Returns a list of JSON dicts, one per form field, containing
        metadata for each field.
        """
        # return cached copy if available
        if self._fields_cache is not None:
            return self._fields_cache

        # get info from the API and save in cache
        api_response = self.formstack.form(self.id)
        fields = api_response.pop('fields')
        self._info_cache = api_response
        self._fields_cache = fields
        return fields

    def _submissions_cache_key(self):
        return 'formstackform_submissions_{}'.format(self.id)
    _submissions_cache = cached_property(_submissions_cache_key)

    def get_submissions(self):
        """
        Returns a list of FormstackSubmission objects, one for each form submission.
        """
        # return cached copy if available
        if self._submissions_cache is not None:
            submissions = []
            for submission_id in self._submissions_cache:
                submission = FormstackSubmission(submission_id, self.formstack)
                submissions.append(submission)
            return submissions

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
            submission._data_cache = submission_doc['data']
            submission.formstack = self.formstack
            submissions.append(submission)
        self._submissions_cache = [submission.id for submission in submissions]
        return submissions

class FormstackSubmission(object):
    """
    A Formstack form submission.
    """

    def __init__(self, submission_id, formstack=None):
        self.id = submission_id
        self.formstack = formstack
        if formstack is not None and self._data_cache is None:
            self.get_data()

    def __unicode__(self):
        return unicode(self.id)

    def __repr__(self):
        return u'<FormstackSubmission: {0}>'.format(self)

    def _data_cache_key(self):
        return 'formstacksubmission_data_{}'.format(self.id)
    _data_cache = cached_property(_data_cache_key)

    def get_data(self):
        """
        Returns the raw submitted data as a JSON dict.
        """
        # return cached copy if available
        if self._data_cache is not None:
            return self._data_cache

        # get data from the API and save in cache
        api_response = self.formstack.submission(self.id)
        self._data_cache = api_response['data']
        return api_response['data']
