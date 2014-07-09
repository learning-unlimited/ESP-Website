from esp.accounting_core.models import LineItemType, Balance, Transaction, LineItem
from anonymizer import Anonymizer

class LineItemTypeAnonymizer(Anonymizer):

    model = LineItemType

    attributes = [
        ('id', "SKIP"),
        ('text', "lorem"),
        ('amount', "decimal"),
        ('anchor_id', "SKIP"),
        ('finaid_amount', "decimal"),
        ('finaid_anchor_id', "SKIP"),
    ]


class BalanceAnonymizer(Anonymizer):

    model = Balance

    attributes = [
        ('id', "SKIP"),
        ('anchor_id', "SKIP"),
        ('user_id', "SKIP"),
        ('timestamp', "datetime"),
        ('amount', "decimal"),
        ('past_id', "SKIP"),
        ('_order', "integer"),
    ]


class TransactionAnonymizer(Anonymizer):

    model = Transaction

    attributes = [
        ('id', "SKIP"),
        ('timestamp', "datetime"),
        ('text', "lorem"),
        ('complete', "bool"),
    ]


class LineItemAnonymizer(Anonymizer):

    model = LineItem

    attributes = [
        ('id', "SKIP"),
        ('transaction_id', "SKIP"),
        ('user_id', "SKIP"),
        ('anchor_id', "SKIP"),
        ('amount', "decimal"),
        ('text', "lorem"),
        ('li_type_id', "SKIP"),
        ('posted_to_id', "SKIP"),
    ]
