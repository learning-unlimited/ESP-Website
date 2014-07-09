from esp.miniblog.models import AnnouncementLink, Entry, Comment
from anonymizer import Anonymizer

class AnnouncementLinkAnonymizer(Anonymizer):

    model = AnnouncementLink

    attributes = [
        ('id', "SKIP"),
        ('title', "varchar"),
        ('category', "varchar"),
        ('timestamp', "datetime"),
        ('highlight_begin', "datetime"),
        ('highlight_expire', "datetime"),
        ('section', "varchar"),
        ('href', "varchar"),
    ]


class EntryAnonymizer(Anonymizer):

    model = Entry

    attributes = [
        ('id', "SKIP"),
        ('title', "varchar"),
        ('slug', "SKIP"),
        ('timestamp', "datetime"),
        ('highlight_begin', "datetime"),
        ('highlight_expire', "datetime"),
        ('content', "lorem"),
        ('sent', "bool"),
        ('email', "bool"),
        ('fromuser_id', "SKIP"),
        ('fromemail', "varchar"),
        ('priority', "integer"),
        ('section', "varchar"),
    ]


class CommentAnonymizer(Anonymizer):

    model = Comment

    attributes = [
        ('id', "SKIP"),
        ('author_id', "SKIP"),
        ('entry_id', "SKIP"),
        ('post_ts', "datetime"),
        ('subject', "varchar"),
        ('content', "lorem"),
    ]
