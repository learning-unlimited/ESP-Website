"""Printable PDF for one deposit slip (letter size).

Page(s) 1: ESP's copy -- what to write on the Bank of America deposit ticket, then the check list.
Then a clean check list for Bank of America and one for SOLE, each starting on a new page, to paperclip
to their copies of the ticket. Long lists continue onto further pages; a running line at the top of each
continued page says which ticket and copy it belongs to.
"""
import io
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

CLEAN_COPIES = ('Bank of America copy', 'SOLE copy')

TITLE = ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=14, leading=17)
SUB = ParagraphStyle('sub', fontName='Helvetica', fontSize=10, leading=13)
BODY = ParagraphStyle('body', fontName='Helvetica', fontSize=10, leading=13)
WARN = ParagraphStyle('warn', fontName='Helvetica-Bold', fontSize=11, leading=14, borderColor=colors.black,
                      borderWidth=1.5, borderPadding=5)
FOOT = ParagraphStyle('foot', fontName='Helvetica-Bold', fontSize=10, leading=13)


def money(a):
    d = Decimal(a)
    return f'${d:,.2f}'


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def heading(title, sub):
    t = Table([[Paragraph(esc(title), TITLE)], [Paragraph(esc(sub), SUB)]], colWidths=[7.5 * inch])
    t.setStyle(TableStyle([('LINEBELOW', (0, -1), (-1, -1), 1.5, colors.black),
                           ('LEFTPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, -1), (-1, -1), 6)]))
    return [t, Spacer(1, 8)]


def discarded(s):
    if not s['superseded']:
        return []
    return [Paragraph('DISCARDED — this slip was replaced; void any paper ticket made from it.', WARN), Spacer(1, 10)]


def totals_table(s):
    rows = [['Currency', money(s['currency'])], ['Coins', money(s['coins'])],
            [f'Checks ({s["total_items"]})', money(s['checks_total'])], ['TOTAL', money(s['total'])]]
    t = Table(rows, colWidths=[1.4 * inch, 1.2 * inch], hAlign='LEFT')
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 11), ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 11),
        ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 11), ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 1.2, colors.black), ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1)]))
    return [t, Spacer(1, 10)]


def check_table(s, copy):
    running = (f'{s["account_label"]} · {s["date"]} · ticket {s["slip_no"]} of {s["n_in_set"]} · {copy} · '
               f'{s["total_items"]} checks, {money(s["checks_total"])}')
    rows = [[running, '', ''], ['Line', 'Check number', 'Amount']]
    rows += [[str(c['line']), c['check_number'], money(c['amount'])] for c in s['checks']]
    t = Table(rows, colWidths=[0.8 * inch, 4.2 * inch, 2.5 * inch], repeatRows=2)
    t.setStyle(TableStyle([
        ('SPAN', (0, 0), (-1, 0)), ('FONT', (0, 0), (-1, 0), 'Helvetica', 8), ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#444444')),
        ('FONT', (0, 1), (-1, 1), 'Helvetica-Bold', 10), ('LINEBELOW', (0, 1), (-1, 1), 1, colors.black),
        ('FONT', (0, 2), (-1, -1), 'Helvetica', 10), ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
        ('LINEBELOW', (0, 2), (-1, -1), 0.4, colors.HexColor('#999999')),
        ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2), ('LEFTPADDING', (0, 0), (-1, -1), 3)]))
    return [t, Spacer(1, 6),
            Paragraph(esc(f'{s["total_items"]} checks · checks total {money(s["checks_total"])} · {s["account_label"]}'), FOOT)]


def esp_copy(s):
    guide = [('Prepared By', s['prepared_by']), ('Deposited By', s['deposited_by']),
             ('BAG #', s['bag_number'] or '(leave blank)'), ('DATE', s['date']),
             ('CURRENCY', money(s['currency'])), ('COINS', money(s['coins'])), ('CHECKS (top box)', money(s['checks_total'])),
             ('Check lines 1–28', 'write "SEE ATTACHED LIST"'), ('TOTAL $', money(s['total'])),
             ('TOTAL ITEMS', str(s['total_items'])), ('Blank area (left side)', s['account_label'])]
    t = Table([list(r) for r in guide], colWidths=[2.6 * inch, 4.9 * inch])
    t.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 12), ('FONT', (1, 0), (1, -1), 'Helvetica', 12),
        ('GRID', (0, 0), (-1, -1), 0.8, colors.black), ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
    batch = s['batch']
    return (heading(f'{s["account_label"]} — ESP copy: deposit ticket fill-in guide + check list',
                    f'{s["date"]} · ticket {s["slip_no"]} of {s["n_in_set"]} · {batch["program_name"]} batch {batch["program_batch"]}')
            + discarded(s)
            + [Paragraph('Write these on the deposit ticket. Paperclip the Bank of America and SOLE check lists '
                         '(next pages) to their copies of the ticket.', BODY), Spacer(1, 8), t, Spacer(1, 14)]
            + check_table(s, 'ESP copy'))


def clean_copy(s, copy):
    batch = s['batch']
    sub = f'{s["date"]} · ticket {s["slip_no"]} of {s["n_in_set"]} · {batch["program_name"]} batch {batch["program_batch"]}'
    if s['bag_number']:
        sub += f' · bag #{s["bag_number"]}'
    return (heading(f'{s["account_label"]} — check list attached to deposit ticket', f'{sub} · {copy}')
            + discarded(s) + totals_table(s) + check_table(s, copy))


def build(s):
    """s: the dict from checkscan.slip_detail(). Returns PDF bytes."""
    buf = io.BytesIO()
    batch = s['batch']
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.5 * inch, rightMargin=0.5 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.5 * inch,
                            title=f'Deposit ticket {s["slip_no"]} of {s["n_in_set"]} — {batch["program_name"]} batch {batch["program_batch"]}',
                            author='ESP check scanner')
    story = esp_copy(s)
    for copy in CLEAN_COPIES:
        story += [PageBreak()] + clean_copy(s, copy)
    doc.build(story)
    return buf.getvalue()
