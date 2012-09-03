from django.db import models
from esp.formstack.api import Formstack
from urllib import urlencode

class FormstackForm(models.Model):
    """
    A Formstack form.

    This is a thin wrapper around a Form ID that contains some extra info
    and utility functions. For accessing the Formstack API, see
    esp.formstack.api.
    """

    id      = models.IntegerField(primary_key=True)
    name    = models.CharField(max_length=80)
    viewkey = models.CharField(max_length=80)

    def __unicode__(self):
        return self.name
    
    @staticmethod
    def get_forms_for_api_key(api_key, save=True):
        """ Returns a list of FormstackForms in an account. """
        api_response = Formstack(api_key).forms()
        forms = []
        for form_doc in api_response['forms']:
            form = FormstackForm(
                id      = int(form_doc['id']),
                name    = form_doc['name'],
                viewkey = form_doc['viewkey'],
                )
            forms.append(form)
            if save:
                form.save()
        return forms

    @property
    def url(self):
        return self.get_url()

    def get_url(self, args={}):
        """ Returns the URL for viewing the form. """

        result = 'http://www.formstack.com/forms/?{}-{}&{}'
        result = result.format(self.id, self.viewkey, urlencode(args))
        return result

    def get_javascript(self, args={}):
        """ Returns as a string the Javascript code for embedding the form. """

        result =  """\
<script type="text/javascript" src="http://www.formstack.com/forms/js.php?{form}-{viewkey}-v2&{args}"></script>
<noscript><a href="http://www.formstack.com/forms/?{form}-{viewkey}&{args}" title="Online Form">Online Form - {name}</a></noscript>
"""
        result = result.format(form=self.id,
                               viewkey=self.viewkey,
                               name=self.name,
                               args=urlencode(args))
        return result
