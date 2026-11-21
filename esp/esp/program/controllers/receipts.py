"""Receipts handed out on the day of the program: for a student's account
(day-of troubleshooting) or an anonymous help desk sale.

A receipt's content is worked out once and frozen in Receipt.lines_json, so
reprints are identical. For a student, staff pick which of their items to
include (all by default). What covered each chosen item is worked out here,
not from Transfer.paid_in (which links items to whichever payment pushed the
running total past them, so an aid-covered fee can end up linked to a cash
payment):
  1. the sibling discount applies to admission items, in item order;
  2. financial aid applies to aid-covered items, in item order, each item
     taking as much of the remaining aid as it costs;
  3. what's left of each item is matched to payments oldest first.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import json
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from esp.accounting.controllers import IndividualAccountingController
from esp.accounting.models import Receipt, Transfer
from esp.tagdict.models import Tag
from esp.users.models import Record

ZERO = Decimal('0')


class ReceiptError(ValueError):
    pass


def _date(dt):
    return timezone.localtime(dt).strftime('%m/%d/%Y') if timezone.is_aware(dt) else dt.strftime('%m/%d/%Y')


def _method_label(payment):
    if payment.payment_method == 'card':
        label = 'card'
        if payment.transaction_id:
            label += ', transaction %s' % payment.transaction_id
    elif payment.payment_method == 'cash_check':
        label = 'cash/check'
    else:
        label = 'payment'
    return label


def student_items(program, student):
    """ The student's items that can go on a receipt, oldest first. """
    iac = IndividualAccountingController(program, student)
    return list(iac.get_transfers().filter(line_item__for_payments=False).exclude(
        line_item__text__in=iac.finaid_items).select_related('line_item', 'option').order_by('id'))


def can_have_receipt(program, student):
    """ Receipts are only for students who are checked in (so paid at
    check-in or since) or have paid by card. """
    if Record.objects.filter(user=student, program=program, event__name='attended').exists():
        return True
    return Transfer.objects.filter(user=student, source__isnull=True, line_item__for_payments=True,
                                   line_item__program=program, payment_method='card').exists()


def allocate(program, student):
    """ For each of the student's items (in order): {'transfer', 'discount',
    'aid', 'payments': [(payment, amount)], 'unpaid'}. """
    iac = IndividualAccountingController(program, student)
    items = student_items(program, student)
    sibling_left = iac.amount_siblingdiscount()
    aid_left = iac.amount_finaid()
    payments = [[p, p.amount_dec] for p in Transfer.objects.filter(
        user=student, source__isnull=True, line_item=iac.default_payments_lineitemtype()).order_by('timestamp', 'id')]
    result = []
    for t in items:
        cost = t.amount_dec
        discount = ZERO
        if t.line_item.text in iac.admission_items and sibling_left > 0:
            discount = min(cost, sibling_left)
            sibling_left -= discount
        aid = ZERO
        if t.line_item.for_finaid and aid_left > 0:
            aid = min(cost - discount, aid_left)
            aid_left -= aid
        left = cost - discount - aid
        paid_by = []
        for entry in payments:
            if left <= 0:
                break
            if entry[1] <= 0:
                continue
            take = min(left, entry[1])
            entry[1] -= take
            left -= take
            paid_by.append((entry[0], take))
        result.append({'transfer': t, 'discount': discount, 'aid': aid, 'payments': paid_by, 'unpaid': left})
    return result


def student_receipt_content(program, student, item_ids, payer_name=''):
    """ The frozen content of a receipt for the chosen items. """
    chosen = [a for a in allocate(program, student) if a['transfer'].id in set(item_ids)]
    if not chosen:
        raise ReceiptError('Pick at least one item for the receipt.')
    lines = []
    for a in chosen:
        t = a['transfer']
        desc = '%s %s' % (program.niceName(), t.line_item.text)
        if t.option is not None:
            desc += ' (%s)' % t.option.description
        _add_line(lines, desc, t.amount_dec)
    discount = sum((a['discount'] for a in chosen), ZERO)
    aid = sum((a['aid'] for a in chosen), ZERO)
    paid = {}
    for a in chosen:
        for (payment, amount) in a['payments']:
            paid.setdefault(payment.id, [payment, ZERO])[1] += amount
    payments = [{'label': 'Paid (%s, %s)' % (_method_label(p), _date(p.timestamp)), 'amount': '%.2f' % amt}
                for (p, amt) in sorted(paid.values(), key=lambda pa: (pa[0].timestamp, pa[0].id))]
    adjustments = []
    if discount:
        adjustments.append({'label': 'Sibling discount', 'amount': '%.2f' % -discount})
    if aid:
        adjustments.append({'label': 'Financial aid', 'amount': '%.2f' % -aid})
    dates = [p.timestamp for (p, amt) in paid.values()]
    content = _content(program, payer_name or student.name(), max(dates) if dates else timezone.now(),
                       lines, adjustments, payments)
    #   So a mistaken receipt can be remade with the same items preselected
    content['item_ids'] = sorted(a['transfer'].id for a in chosen)
    content['payer_name_given'] = payer_name
    return content


def sale_receipt_content(sale, payer_name=''):
    if sale.status != 'paid':
        raise ReceiptError('Sale #%d isn\'t paid, so it can\'t have a receipt.' % sale.id)
    lines = []
    for line in sale.lines.select_related('line_item', 'option').order_by('id'):
        desc = '%s %s' % (sale.program.niceName(), line.line_item.text)
        if line.option is not None:
            desc += ' (%s)' % line.option.description
        _add_line(lines, desc, line.unit_price_dec, line.quantity)
    if not lines:
        _add_line(lines, sale.description or 'Help desk purchase', sale.total_dec)
    if sale.method == 'card':
        label = 'Paid (card%s, %s)' % (', transaction %s' % sale.transaction_id if sale.transaction_id else '',
                                       _date(sale.paid_at or sale.created_at))
    else:
        label = 'Paid (cash/check, %s)' % _date(sale.paid_at or sale.created_at)
    return _content(sale.program, payer_name or sale.payer_name, sale.paid_at or sale.created_at, lines, [],
                    [{'label': label, 'amount': '%.2f' % sale.total_dec}])


def _add_line(lines, desc, unit, quantity=1):
    """ Adds an item line, merging it into an identical earlier one. """
    for line in lines:
        if line['description'] == desc and line['unit'] == '%.2f' % unit:
            line['quantity'] += quantity
            line['amount'] = '%.2f' % (Decimal(line['unit']) * line['quantity'])
            return
    lines.append({'description': desc, 'quantity': quantity, 'unit': '%.2f' % unit,
                  'amount': '%.2f' % (unit * quantity)})


def _content(program, payer_name, date, lines, adjustments, payments):
    subtotal = sum((Decimal(l['amount']) for l in lines), ZERO)
    paid = sum((Decimal(p['amount']) for p in payments), ZERO)
    adjusted = sum((Decimal(a['amount']) for a in adjustments), ZERO)
    return {
        'from': (Tag.getProgramTag('receipt_from_address', program) or '').strip().splitlines(),
        'payer': payer_name,
        'date': _date(date),
        'lines': lines,
        'subtotal': '%.2f' % subtotal,
        'adjustments': adjustments,
        'payments': payments,
        'paid': '%.2f' % paid,
        'amount_due': '%.2f' % (subtotal + adjusted - paid),
    }


def create_receipt(program, content, recorded_by, user=None, sale=None):
    """ Saves a receipt with the program's next number. """
    for _ in range(5):  # unique_together guards against two being numbered at once
        top = Receipt.objects.filter(program=program).order_by('-number').values_list('number', flat=True).first()
        try:
            with transaction.atomic():
                return Receipt.objects.create(
                    program=program, number=(top or 0) + 1, user=user, sale=sale,
                    payer_name=content['payer'], lines_json=json.dumps(content),
                    recorded_by=recorded_by)
        except IntegrityError:
            continue
    raise ReceiptError('Could not number the receipt; please try again.')


def receipt_content(receipt):
    content = json.loads(receipt.lines_json)
    content['number'] = receipt.number
    content['void'] = receipt.voided_at is not None
    return content


def receipt_pdf(receipt):
    """ The receipt as a one-page letter PDF. """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape

    c = receipt_content(receipt)
    body = ParagraphStyle('body', fontName='Helvetica', fontSize=10, leading=13)
    bold = ParagraphStyle('bold', parent=body, fontName='Helvetica-Bold')
    title = ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=34, leading=38)

    from_lines = [Paragraph(escape(line), bold if i == 0 else body) for (i, line) in enumerate(c['from'])]
    header = Table([[Paragraph('RECEIPT' + (' (VOID)' if c['void'] else ''), title), from_lines]],
                   colWidths=[3.6 * inch, 3.4 * inch])
    header.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))

    info_rows = []
    if c['payer']:
        info_rows.append(['Payment By:', c['payer']])
    info_rows += [['Date:', c['date']], ['Receipt #:', str(c['number'])]]
    info = Table([[Paragraph(escape(a), body), Paragraph(escape(b), body)] for (a, b) in info_rows],
                 colWidths=[1.0 * inch, 4.0 * inch], hAlign='LEFT')

    rows = [['DESCRIPTION', 'QUANTITY', 'UNIT PRICE', 'AMOUNT']]
    for line in c['lines']:
        rows.append([Paragraph(escape(line['description']), body), '%.2f' % line['quantity'],
                     '$%s' % line['unit'], '$%s' % line['amount']])
    n_items = len(rows)
    totals = [('SUBTOTAL', c['subtotal'])]
    totals += [(a['label'].upper(), a['amount']) for a in c['adjustments']]
    totals += [(p['label'], p['amount']) for p in c['payments']]
    totals += [('AMOUNT DUE', c['amount_due'])]
    for (label, amount) in totals:
        neg = amount.startswith('-')
        rows.append(['', Paragraph(escape(label), ParagraphStyle('r', parent=body, alignment=2)), '',
                     '%s$%s' % ('-' if neg else '', amount.lstrip('-'))])
    table = Table(rows, colWidths=[3.3 * inch, 1.1 * inch, 1.2 * inch, 1.4 * inch], repeatRows=1)
    style = [
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOX', (0, 0), (-1, n_items - 1), 1, colors.black),
        ('GRID', (0, 0), (-1, n_items - 1), 0.5, colors.black),
        ('BOX', (3, n_items), (3, -1), 0.5, colors.black),
        ('INNERGRID', (3, n_items), (3, -1), 0.5, colors.black),
        ('SPAN', (1, n_items), (2, n_items)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONT', (1, len(rows) - 1), (-1, len(rows) - 1), 'Helvetica-Bold'),
    ]
    for r in range(n_items, len(rows)):
        style.append(('SPAN', (1, r), (2, r)))
    for r in range(2, n_items, 2):
        style.append(('BACKGROUND', (0, r), (-1, r), colors.HexColor('#dddddd')))
    table.setStyle(TableStyle(style))

    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch,
                            title='Receipt %d' % c['number'])
    doc.build([header, Spacer(1, 0.3 * inch), info, Spacer(1, 0.3 * inch), table])
    return out.getvalue()


@transaction.atomic
def void_receipt(receipt, voided_by):
    if receipt.voided_at is None:
        receipt.voided_at = timezone.now()
        receipt.voided_by = voided_by
        receipt.save()


#   Shared view helpers (used by the troubleshooting and help desk modules)

def receipt_page(request, receipt, urls):
    """ The receipt's page: preview, print, void. urls: pdf, void, back. """
    from esp.utils.web import render_to_response
    return render_to_response('program/modules/dayof/receipt.html', request, {
        'receipt': receipt, 'content': receipt_content(receipt), 'urls': urls,
        'program': receipt.program,
    })


def pdf_response(receipt):
    from django.http import HttpResponse
    response = HttpResponse(receipt_pdf(receipt), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="receipt-%d.pdf"' % receipt.number
    return response
