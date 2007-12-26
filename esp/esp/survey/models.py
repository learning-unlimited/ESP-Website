" Survey models for Educational Studies Program. "

__author__    = "$LastChangedBy$"
__date__      = "$LastChangedDate$"
__rev__       = "$LastChangedRevision$"
__headurl__   = "$HeadURL$"
__license__   = "GPL v2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""

import datetime
from django.db import models
from django.template import loader
from django.core.cache import cache


try:
    import cPickle as pickle
except ImportError:
    import pickle

from esp.db.fields import AjaxForeignKey

# Models to depend on.
from esp.datatree.models import DataTree
from esp.middleware import ESPError
from esp.program.models import Class, Program

class ListField(object):
    """ Create a list type field descriptor. Allows you to 
    pack lists (actually tuples) into a delimited string easily.

    Example Usage:
        class A(models.Model):
            b = models.TextField()
            a = ListField('b')
    
        c = A()

        c.a = ('a','b','c')

        print c.b
        >>> "a|b|c"

        c.save()

    """        
    field_name = ''
    separator = '|'

    def __init__(self, field_name, separator='|'):
        self.field_name = field_name
        self.separator = separator

    def __get__(self, instance, class_):
        data = str(getattr(instance, self.field_name) or '').strip()
        if not data:
            return ()
        else:
            return tuple(str(data).split(self.separator))

    def __set__(self, instance, value):
        data = self.separator.join(map(str, value))
        setattr(instance, self.field_name, data)


class Survey(models.Model):
    """ A single survey. """
    name = models.CharField(maxlength=255)
    anchor = AjaxForeignKey(DataTree, related_name='surveys',
                            help_text="Usually the program.")

    category = models.CharField(maxlength=32) # teach|learn|etc
    
    def __str__(self):
        return '%s (%s) for %s' % (self.name, self.category, str(self.anchor))
    
    def num_participants(self):
        #   If there is a program anchored to the anchor, select the appropriate number
        #   of participants based on the category.
        progs = Program.objects.filter(anchor=self.anchor)
        if progs.count() == 1:
            prog = progs[0]
            if self.category == 'teach':
                return prog.num_teachers()['class_rejected']
            elif self.category == 'learn':
                return prog.num_students()['confirmed']
            else:
                return 0
        else:
            return 0
        
    class Admin:
        pass


class SurveyResponse(models.Model):
    """ A single survey taken by a person. """
    time_filled = models.DateTimeField(default=datetime.datetime.now)
    survey = models.ForeignKey(Survey, db_index=True)

    def set_answers(self, get_or_post, save=False):
        """ For a given get or post, get a set of answers. """
        answers = []

        keys = filter(lambda x: x.startswith('question_'), get_or_post.keys())
        for key in keys:
            value = get_or_post.getlist(key)
            if len(value) == 1: value = value[0]
            str_list = key.split('_')
            if len(str_list) < 2 or len(str_list) > 3:
                raise ESPError(), 'Inappropriate question key: %s' % key
            
            new_answer = Answer()
            new_answer.survey_response = self
            
            if len(str_list) > 2:
                try:
                    qid = int(str_list[1])
                    cid = int(str_list[2])
                    question = Question.objects.get(id=qid)
                    cls = Class.objects.get(id=cid)
                except Class.DoesNotExist:
                    raise ESPError(), 'Error finding class from %s' % key
                except Question.DoesNotExist:
                    raise ESPError(), 'Error finding question from %s' % key
                except ValueError:
                    raise ESPError(), 'Error getting IDs from %s' % key

                new_answer.anchor = cls.anchor
                
            elif len(str_list) == 2:
                try:
                    qid = int(str_list[1])
                    question = Question.objects.get(id=qid)
                except Question.DoesNotExist:
                    raise ESPError(), 'Error finding question from %s' % key
                except ValueError:
                    raise ESPError(), 'Error getting IDs from %s' % key
                new_answer.anchor = self.survey.anchor
                
            if not isinstance(value, basestring):
                new_answer.value = '+' + pickle.dumps(value)
            else:
                new_answer.value = ':' + value
            new_answer.question = question 
            answers.append(new_answer)

        if save:
            for answer in answers:
                answer.save()

        return answers
            
    class Admin:
        pass
    
    def __str__(self):
        return "Survey for %s filled out at %s" % (self.survey.anchor,
                                                   self.time_filled)


class QuestionType(models.Model):
    """ A type of question.
    Examples:
        - Yes/No
        - Rate from 1-5
        - Free Response short
        - Free Response long
    """

    name = models.CharField(maxlength=255)
    _param_names = models.TextField("Parameter names", blank=True,
                                    help_text="A pipe (|) delimited list of parameter names.")
    param_names = ListField('_param_names')
    is_numeric = models.BooleanField(null=True)

    @property
    def template_file(self):
        return 'survey/questions/%s.html' % self.name.replace(' ', '_').lower()
    
    @property
    def answers_template_file(self):
        return 'survey/answers/%s.html' % self.name.replace(' ', '_').lower()

    def __str__(self):
        return '%s: includes %s' % (self.name, self._param_names.replace('|', ', '))

    class Admin:
        pass


class Question(models.Model):
    survey = models.ForeignKey(Survey, related_name="questions")
    name = models.CharField(maxlength=255)
    question_type = models.ForeignKey(QuestionType)
    _param_values = models.TextField("Parameter values", blank=True,
                                     help_text="A pipe (|) delimited list of values.")
    param_values = ListField('_param_values')
    anchor = AjaxForeignKey(DataTree, related_name="questions", help_text="What is this quesiton related to?")
    seq = models.IntegerField(default=0)

    def get_params(self):
        " Get the parameters for this question, as a dictionary. "
        
        a, b = self.question_type.param_names, self.param_values
        params = dict(zip(map(lambda x: x.replace(' ', '_').lower(), a),
                          b))
        min_length = min(len(a), len(b))
        params['list'] = b[min_length:]

        return params

    def __str__(self):
        return '%s, %d: "%s" (%s)' % (self.survey.name, self.seq, self.name, self.question_type.name)

    def get_value(self, data_dict):
        question_key = 'question_%s' % self.id

        try:
            value = data_dict.getlist(question_key)
            if len(value) == 1:
                value = value[0]
        except AttributeError:
            value = data_dict.get(question_key, None)

        return value
    
    def render(self, data_dict=None):
        """ Render this question to text (usually HTML).

        If specified, data_dict will contain the pre-filled data
        from a GET or POST operation.
        """

        ##########
        # Get any pre-filled data
        if not data_dict:
            data_dict = {}
        value = self.get_value(data_dict)

        ##########
        # Render the HTML
        params = self.get_params()
        params['name'] = self.name
        params['id'] = self.id
        params['value'] = value
        
        if self.anchor.name == 'Classes':
            params['for_class'] = True

        return loader.render_to_string(self.question_type.template_file, params)

    def dump(self, data_dict=None):
        """ Dump this question's responses.
        
        If specified, data_dict will contain the pre-filled data
        from a GET or POST operation. Probably not relevant here.
        
        So far, it differs from question.render only in its template files.
        """

        ##########
        # Get any pre-filled data
        if not data_dict:
            data_dict = {}
        value = self.get_value(data_dict)

        ##########
        # Render the HTML
        params = self.get_params()
        params['name'] = self.name
        params['id'] = self.id
        params['value'] = value
        
        if self.anchor.name == 'Classes':
            params['for_class'] = True

        return loader.render_to_string(self.question_type.answers_template_file, params)

    def global_average(self):
        def pretty_val(val):
            if val == 0:
                return 'N/A'
            else:
                return str(round(val, 2))
        
        if not self.question_type.is_numeric:
            return None
        
        try:
            average_key = 'question_%d_avg' % self.id
            
            test_val = cache.get(average_key)
            if test_val is None:
                ans = Answer.objects.filter(question=self)
                ans_count = ans.count()
                ans_sum = 0.0
                for a in ans:
                    ans_sum += float(a.answer)
                if ans_count == 0:
                    new_val = 0
                else:
                    new_val = ans_sum / ans_count;
                cache.set(average_key, new_val)
                return pretty_val(new_val)
            else:
                return pretty_val(test_val)
        except:
            return 'N/A'

    class Admin:
        pass
    
    class Meta:
        ordering = ['seq']


class Answer(models.Model):
    """ An answer for a single question for a single survey response. """

    survey_response = models.ForeignKey(SurveyResponse, db_index=True,
                                        related_name='answers')
    anchor = AjaxForeignKey(DataTree)                                        
    question = models.ForeignKey(Question, db_index=True)
    value = models.TextField()

    @property
    def answer(self):
        """ The actual, unpickled answer. """
        if not self.value:
            return None

        if self.value[0] == '+':
            try:
                value = pickle.loads(self.value[1:])
            except:
                value = self.value[1:]
        else:
            value = self.value[1:]

        return value


    class Admin:
        pass

    def __str__(self):
        return "Answer for question #%d: %s" % (self.question.id, self.value)
