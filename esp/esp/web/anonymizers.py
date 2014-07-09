from esp.web.models import NavBarCategory, NavBarEntry
from anonymizer import Anonymizer

class NavBarCategoryAnonymizer(Anonymizer):

    model = NavBarCategory

    attributes = [
        ('id', "SKIP"),
        ('anchor_id', "SKIP"),
        ('include_auto_links', "bool"),
        ('name', "name"),
        ('path', "varchar"),
        ('long_explanation', "lorem"),
    ]


class NavBarEntryAnonymizer(Anonymizer):

    model = NavBarEntry

    attributes = [
        ('id', "SKIP"),
        ('path_id', "SKIP"),
        ('sort_rank', "integer"),
        ('link', "varchar"),
        ('text', "varchar"),
        ('indent', "bool"),
        ('category_id', "SKIP"),
    ]
