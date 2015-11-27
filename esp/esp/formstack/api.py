# The MIT License
#
# Copyright (c) 2010 Formstack, LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import urllib
import urllib2
import json

class Formstack(object):

    def __init__(self, api_key):

        self.__api_url = 'https://www.formstack.com/api'
        self.__api_key = api_key

    def forms(self):
        """
        Returns a list of forms in an account. The response includes all of the
        information returned by the form method, with the exception of
        information about each form field and the HTML or JavaScript required to
        display the form.
        """

        return self.__request('forms')

    def form(self, id, args = {}):
        """Returns detailed information about a form."""

        args['id'] = id
        return self.__request('form', args)

    def data(self, id, args = {}):
        """Returns data collected for a form."""

        args['id'] = id
        return self.__request('data', args)

    def submission(self, id, args = {}):
        """Returns a single submission collected for a form."""

        args['id'] = id
        return self.__request('submission', args)

    def submit(self, id, args = {}):
        """
        Submits data to a form. This method does not honor any
        validation or default values configured for a field. because of the lack
        of validation checks, it is not intended for day-to-day use for public
        submissions. The form must be configured to store submissions in the
        database. An error will be returned if the maximum number of submissions
        for the account has been reached.
        """

        args['id'] = id
        return self.__request('submit', args)

    def edit(self, id, args = {}):
        """
        This method makes changes to an existing submission. Only values
        supplied within args will be overwritten.
        """

        args['id'] = id
        return self.__request('edit', args)

    def delete(self, id, args = {}):
        """Deletes an existing submission."""

        args['id'] = id
        return self.__request('delete', args)

    def create_field(self, form, args = {}):
        """ Creates a field."""

        args['form'] = form
        return self.__request('createField', args)

    def __request(self, method, args = {}):
        """ Makes a Formstack API call and returns the response as an array."""

        args['api_key'] = self.__api_key
        args['type'] = 'json'
        req = urllib2.Request(self.__api_url + '/' + method, \
                              urllib.urlencode(args))
        try:

            res = urllib2.urlopen(req)
            res = json.load(res)

            if len(res) and res['status'] == 'ok':
                return res['response']
            elif len(res) and res['status'] == 'error':
                raise APIError(res['error'])
            else:
                raise APIError('Unknown Error')

        # I don't know what they were thinking with try ... except: pass
        # --lua
        except urllib2.URLError as e:
            raise APIError(e)

        return None

class APIError(Exception):
    def __str__(self):
        return 'Formstack API error: {0}'.format(self.message)
