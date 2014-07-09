from esp.accounting.models import LineItemType, LineItemOptions, FinancialAidGrant, Account, Transfer
from anonymizer import Anonymizer

class LineItemTypeAnonymizer(Anonymizer):

    model = LineItemType

    attributes = [
        ('id', "SKIP"),
        ('text', "lorem"),
        ('amount_dec', "decimal"),
        ('program_id', "SKIP"),
        ('required', "bool"),
        ('max_quantity', "positive_integer"),
        ('for_payments', "bool"),
        ('for_finaid', "bool"),
    ]


class LineItemOptionsAnonymizer(Anonymizer):

    model = LineItemOptions

    attributes = [
        ('id', "SKIP"),
        ('lineitem_type_id', "SKIP"),
        ('description', "lorem"),
        ('amount_dec', "decimal"),
    ]


class FinancialAidGrantAnonymizer(Anonymizer):

    model = FinancialAidGrant

    attributes = [
        ('id', "SKIP"),
        ('request_id', "SKIP"),
        ('amount_max_dec', "decimal"),
        ('percent', "positive_integer"),
        ('timestamp', "datetime"),
        ('finalized', "bool"),
    ]


class AccountAnonymizer(Anonymizer):

    model = Account

    attributes = [
        ('id', "SKIP"),
        ('name', "name"),
        ('description', "lorem"),
        ('program_id', "SKIP"),
        ('balance_dec', "decimal"),
    ]


class TransferAnonymizer(Anonymizer):

    model = Transfer

    attributes = [
        ('id', "SKIP"),
        ('source_id', "SKIP"),
        ('destination_id', "SKIP"),
        ('user_id', "SKIP"),
        ('line_item_id', "SKIP"),
        ('amount_dec', "decimal"),
        ('transaction_id', "lorem"),
        ('timestamp', "datetime"),
        ('executed', "bool"),
    ]
