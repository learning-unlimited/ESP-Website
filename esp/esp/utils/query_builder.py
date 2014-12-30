import json
import random
import operator

from django.db.models.query import Q
from django.template.loader import render_to_string

from esp.middleware import ESPError

# TODO: finish docstrings once APIs are stable


class QueryBuilder(object):
    def __init__(self, model, filters, english_name=None):
        self.model = model
        self.english_name = (english_name or
                             unicode(model._meta.verbose_name_plural))
        self.filters = filters
        self.filter_dict = {f.name: f for f in filters}

    def spec(self):
        return {
            'englishName': self.english_name,
            'filterNames': [f.name for f in self.filters],
            'filters': {f.name: f.spec() for f in self.filters},
        }

    def as_queryset(self, value):
        base = self.model.objects.all()
        if value['filter'] in ['and', 'or']:
            if value['filter'] == 'and':
                op = operator.and_
            else:
                op = operator.or_
            combined = reduce(op, map(self.as_queryset, value['values']))
            if value['negated']:
                return base.exclude(pk__in=combined)
            else:
                return combined
        elif value['filter'] in self.filter_dict:
            filter_obj = self.filter_dict[value['filter']]
            filter_q = filter_obj.as_q(value['values'])
            if value['negated'] ^ filter_obj.inverted:
                # Due to https://code.djangoproject.com/ticket/14645, we have
                # to write this query a little weirdly.
                return base.exclude(id__in=base.filter(filter_q))
            else:
                return base.filter(filter_q)
        else:
            raise ESPError('Invalid filter %s' % value.get('filter'))

    def as_english(self, value, root=True):
        if root:
            base = '%s with ' % self.english_name
        else:
            base = ''
        if value['filter'] in ['and', 'or']:
            if value['negated'] and value['filter'] == 'or':
                join_word = ' nor '
                intro_word = ' neither'
            else:
                join_word = ' %s ' % value['filter']
                if value['negated']:
                    intro_word = ' none of'
                else:
                    intro_word = ''
            return base + intro_word + join_word.join(
                ['(' + self.as_english(v, root=False) + ')'
                 for v in value['values']])
        elif value['filter'] in self.filter_dict:
            filter_obj = self.filter_dict[value['filter']]
            if value['negated']:
                base = base + 'not '
            return base + filter_obj.as_english(value['values'])
        else:
            raise ESPError('Invalid filter %s' % value.get('filter'))

    def render(self):
        context = {
            # use a uid in case we ever want to have multiple QBs on the same
            # page.
            'uid': random.randrange(0, 1 << 30),
            'json_spec': json.dumps(self.spec()),
        }
        return render_to_string("utils/query_builder.html", context)


class SearchFilter(object):
    """A filter that might appear in a query builder.

    Each instance will be a particular filter type, such as a filter for flags.

    `name` is the internal name; you'll probably be happier in your life if it
        doesn't have spaces.
    `inputs` is a list of inputs, which are instances of classes like
        SelectInput and DateTimeInput.  Many filters will have only a single
        input, but they can have multiple.  Each input should have the
        following methods:
          * name (a property or variable): must be distinct within each filter
          * spec(self): return a dict with a key "reactClass" which can be
            passed to the React class of that name to specify how to draw the
            output.
          * as_q(self, value): given the value of the input, return a Q object
            that can be fed into the filter's QuerySet filter
          * as_english(self, value): likewise, but return a vaguely English
            description
    """
    def __init__(self, name, title=None, inputs=None, inverted=False):
        self.name = name
        self.title = title or self.name
        self.inputs = inputs or []
        self.inverted = inverted

    def spec(self):
        return {
            'name': self.name,
            'title': self.title,
            'inputs': [inp.spec() for inp in self.inputs],
        }

    def as_q(self, value):
        # AND together the Q objects from each input
        return reduce(operator.and_,
                      [i.as_q(v) for i, v in zip(self.inputs, value)])

    def as_english(self, value):
        return self.title + " and ".join([i.as_english(v)
                                          for i, v in zip(self.inputs, value)])


class SelectInput(object):
    """An input represented by a HTML <select> with a fixed set of options.

    `name` should be the field that the input represents; it will be used in
    the returned Q object.
    `options` should be a dict of id -> user-friendly names of the options for
    the select.
    """
    def __init__(self, field_name, options, english_name=None):
        self.field_name = field_name
        self.options = options
        self.english_name = english_name or field_name.replace('_', ' ')

    def spec(self):
        return {
            'reactClass': 'SelectInput',
            'options': [{'name': k, 'title': v}
                        for k, v in self.options.items()],
        }

    def as_q(self, value):
        if value in self.options:
            return Q(**{self.field_name: value})
        else:
            raise ESPError('Invalid choice %s for input %s'
                           % (value, self.field_name))

    def as_english(self, value):
        if value in self.options:
            return "with %s '%s'" % (self.options[value], self.english_name)
        else:
            raise ESPError('Invalid choice %s for input %s'
                           % (value, self.field_name))


class TrivialInput(object):
    """An input which adds a fixed Q object to the query."""
    def __init__(self, q):
        self.q = q

    def spec(self):
        return {'reactClass': 'TrivialInput'}

    def as_q(self, value):
        return self.q

    def as_english(self, value):
        return ""
