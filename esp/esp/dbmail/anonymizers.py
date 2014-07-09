from esp.dbmail.models import MessageRequest, TextOfEmail, MessageVars, EmailRequest, EmailList, PlainRedirect
from anonymizer import Anonymizer

class MessageRequestAnonymizer(Anonymizer):

    model = MessageRequest

    attributes = [
        ('id', "SKIP"),
        ('subject', "lorem"),
        ('msgtext', "lorem"),
        ('special_headers', "lorem"),
        ('recipients_id', "SKIP"),
        ('sendto_fn_name', "choice"),
        ('sender', "lorem"),
        ('creator_id', "SKIP"),
        ('processed', "bool"),
        ('processed_by', "datetime"),
        ('email_all', "bool"),
        ('priority_level', "integer"),
    ]


class TextOfEmailAnonymizer(Anonymizer):

    model = TextOfEmail

    attributes = [
        ('id', "SKIP"),
        ('send_to', "varchar"),
        ('send_from', "varchar"),
        ('subject', "lorem"),
        ('msgtext', "lorem"),
        ('sent', "datetime"),
        ('sent_by', "datetime"),
        ('locked', "bool"),
        ('tries', "integer"),
    ]


class MessageVarsAnonymizer(Anonymizer):

    model = MessageVars

    attributes = [
        ('id', "SKIP"),
        ('messagerequest_id', "SKIP"),
        ('pickled_provider', "lorem"),
        ('provider_name', "name"),
    ]


class EmailRequestAnonymizer(Anonymizer):

    model = EmailRequest

    attributes = [
        ('id', "SKIP"),
        ('target_id', "SKIP"),
        ('msgreq_id', "SKIP"),
        ('textofemail_id', "SKIP"),
    ]


class EmailListAnonymizer(Anonymizer):

    model = EmailList

    attributes = [
        ('id', "SKIP"),
        ('regex', "varchar"),
        ('seq', "positive_integer"),
        ('handler', "varchar"),
        ('subject_prefix', "varchar"),
        ('admin_hold', "bool"),
        ('cc_all', "bool"),
        ('from_email', "email"),
        ('description', "lorem"),
    ]


class PlainRedirectAnonymizer(Anonymizer):

    model = PlainRedirect

    attributes = [
        ('id', "SKIP"),
        ('original', "varchar"),
        ('destination', "varchar"),
    ]
