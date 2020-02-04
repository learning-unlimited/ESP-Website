import random
import json

from django import template

register = template.Library()


@register.inclusion_tag('utils/query_builder.html')
def render_query_builder(qb, query=None):
        """Render a QueryBuilder into HTML.

        query-builder.jsx will need to be included in the page separately.

        `qb` should be a QueryBuilder object.
        `query` should be a jsonifiable object representing the query that
            should be preloaded into the query builder, or may be omitted to
            display an empty query builder.
        """
        context = {
            # use a uid in case we ever want to have multiple QBs on the same
            # page.
            'uid': random.randrange(0, 1 << 30),
            'json_spec': json.dumps(qb.spec()),
            'json_query': json.dumps(query),
        }
        return context
