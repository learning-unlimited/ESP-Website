import datetime
import operator

from django.db.models.query import Q

from esp.middleware import ESPError


class QueryBuilder(object):
    """A class to build complex queries.

    QueryBuilder can be used to create an interface that allows users to build
    complex queries.  This can then be used to generate a django QuerySet of
    matching objects.  The recommended way of including it in a page is with
    the render_query_builder template tag.

    Arguments:
        `base`: the base query to use, such as FooBar.objects.all().
        `filters`: a list of SearchFilter objects representing the filters that
            may be used.
        `english_name`: the english name of the things to search, such as
            "foobar".  May be omitted, in which case the model's name will be used.
    """
    def __init__(self, base, filters, english_name=None):
        self.base = base
        if english_name is None:
            self.english_name = unicode(base.model._meta.verbose_name_plural)
        else:
            self.english_name = english_name
        self.filters = filters
        self.filter_dict = {f.name: f for f in filters}

    def spec(self):
        """Return a specification of the QB to be passed to the client.

        See query-builder.jsx for the format generated.
        """
        return {
            'englishName': self.english_name,
            'filterNames': [f.name for f in self.filters],
            'filters': {f.name: f.spec() for f in self.filters},
        }

    def as_queryset(self, value):
        """Given data returned by the client, return a QuerySet for the query.

        The data returned will be in the format specified in query-builder.jsx.
        """
        if value['filter'] in ['and', 'or']:
            if value['filter'] == 'and':
                op = operator.and_
            else:
                op = operator.or_
            combined = reduce(op, map(self.as_queryset, value['values']))
            if value['negated']:
                return self.base.exclude(pk__in=combined)
            else:
                return combined
        elif value['filter'] in self.filter_dict:
            filter_obj = self.filter_dict[value['filter']]
            filter_q = filter_obj.as_q(value['values'])
            if value['negated'] ^ filter_obj.inverted:
                # Due to https://code.djangoproject.com/ticket/14645, we have
                # to write this query a little weirdly.
                return self.base.exclude(id__in=self.base.filter(filter_q))
            else:
                return self.base.filter(filter_q)
        else:
            raise ESPError('Invalid filter %s' % value.get('filter'))


class SearchFilter(object):
    """A filter that might appear in a query builder.

    Each instance will be a particular filter type, such as a filter for flags
    (which might allow selecting the flag type, modified time, and so on).

    Arguments:
        `name`: the internal name, a string.
        `title`: the human-readable name, a string.
        `inverted`: True if the generated query should be inverted, as an
            .exclude() by default rather than a .filter()
        `inputs`: a list of inputs, which are instances of classes like
            SelectInput and DatetimeInput.  Many filters will have only a
            single input, but they can have multiple.  Each input should have
            the following methods:
                `spec`: return a spec to describe itself to the client, which
                    should include a key 'reactClass' which has value the name
                    of the corresponding React class.  See query-builder.jsx
                    for details.
                `as_q`: given data returned by the client, return the Q object
                    the user has requested.
            The types of values the latter two receive are specified in
            query-builder.jsx.

    In order to design a new input type, one must write both a python class
    (likely in this file) and a React class (likely in query-builder.jsx),
    which generally have the same name, implementing the corresponding input
    class APIs.
    """
    def __init__(self, name, title=None, inputs=None, inverted=False):
        self.name = name
        if title is None:
            self.title = name
        else:
            self.title = title
        self.inputs = inputs or []
        self.inverted = inverted

    def spec(self):
        """Return a specification of the filter to be passed to the client.

        See query-builder.jsx for the format generated.
        """
        return {
            'name': self.name,
            'title': self.title,
            'inputs': [inp.spec() for inp in self.inputs],
        }

    def as_q(self, value):
        """Given data returned by the client, return a Q object for the filter.

        The data returned will be in the format specified in query-builder.jsx.
        """
        # AND together the Q objects from each input
        return reduce(operator.and_,
                      [i.as_q(v) for i, v in zip(self.inputs, value)])


class SelectInput(object):
    """An input represented by an HTML <select> with a fixed set of options.

    Arguments:
        `field_name`: the field that the input represents; it will be used in
            the returned Q object.
        `options`: a dict of ids -> user-friendly names of the options for the
            select.  The ids should be strings.
    """
    def __init__(self, field_name, options):
        self.field_name = field_name
        self.options = options
        # TODO: warn if option ids are not strings.

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


class ConstantInput(object):
    """An input which adds a fixed Q object to the filter.

    Arguments:
        `q`: the Q object to be used.
    """
    def __init__(self, q):
        self.q = q

    def spec(self):
        return {'reactClass': 'ConstantInput'}

    def as_q(self, value):
        return self.q


class OptionalInput(object):
    """An input that can either use or not use another input.

    Arguments:
        `inner`: the input that might be used.
        `name`: the name to go on the button to turn it on and off.
    """
    def __init__(self, inner, name="+"):
        self.inner = inner
        self.name = name

    def spec(self):
        return {
            'reactClass': 'OptionalInput',
            'name': self.name,
            'inner': self.inner.spec(),
        }

    def as_q(self, value):
        if value is None:
            return Q()
        else:
            return self.inner.as_q(value['inner'])


class DatetimeInput(object):
    """An input for before, after, or exactly at a datetime.

    Arguments:
        `field_name`: the DateTimeField to use.
        `english_name`: an English description of the field.  Defaults to
            `field_name`.
    """
    TIME_FMT = "%m/%d/%Y %H:%M"

    def __init__(self, field_name, english_name=None):
        self.field_name = field_name
        if english_name is None:
            english_name = field_name.replace('_', ' ')
        self.english_name = english_name

    def spec(self):
        return {
            'reactClass': 'DatetimeInput',
            'name': self.english_name,
        }

    def as_q(self, value):
        if value['comparison'] == 'before':
            lookup = self.field_name + '__lt'
        elif value['comparison'] == 'after':
            lookup = self.field_name + '__gt'
        else:
            lookup = self.field_name
        dt = datetime.datetime.strptime(value['datetime'], self.TIME_FMT)
        return Q(**{lookup: dt})


class TextInput(object):
    """An input for arbitrary text.

    Arguments:
        `field_name`: the field (possibly including a lookup like __contains)
            against which the text should be queried.
        `english_name`: an English description of the field.  Defaults to
            `field_name`.
    """
    def __init__(self, field_name, english_name=None):
        self.field_name = field_name
        if english_name is None:
            self.english_name = field_name.replace('_', ' ')
        else:
            self.english_name = english_name

    def spec(self):
        return {
            'reactClass': 'TextInput',
            'name': self.english_name,
        }

    def as_q(self, value):
        return Q(**{self.field_name: value})
