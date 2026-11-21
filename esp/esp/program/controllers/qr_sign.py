"""A printable QR code sign (/manage/qrcode): a title (one or more lines), a
QR code of a link, and a caption under it (usually the link, for people
without a camera), each as large as fits on a letter page. The page is laid
out once as a reportlab Drawing, so the live preview (SVG) and the printed
PDF are the same."""
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import re

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

MAX_LINK = 1000         # characters (a QR code holds up to ~2900 bytes, but gets dense)
MAX_TITLE = 200
MAX_TITLE_LINES = 4
MAX_CAPTION = 200

FONT = 'Helvetica-Bold'
PAGE = (612.0, 792.0)   # letter, in points
MARGIN = 36.0           # 0.5 in: also the code's quiet zone, so the code itself has no border
GAP = 24.0              # between the title, the code and the caption
LINE = 1.15             # line height, as a multiple of the font size
MAX_TITLE_SIZE = 120.0
MAX_CAPTION_SIZE = 72.0
MIN_SIZE = 12.0         # making room for the code shrinks the text no smaller than this (fitting the width may)
MIN_CODE = 4 * 72.0     # shrink the text before the code gets smaller than 4 in


class QRSignError(ValueError):
    pass


def default_caption(link):
    """ The link without https:// and a trailing slash, as people would type it. """
    return re.sub(r'^https://', '', link.strip(), flags=re.I).rstrip('/')


def title_lines(title):
    return [line.strip() for line in (title or '').strip().splitlines() if line.strip()]


def clean(title, link, caption):
    """ (title, link, caption) stripped, with the caption defaulted; raises
    QRSignError if they can't make a sign. The title may have several lines. """
    #   (browsers send a textarea's line breaks as \r\n, but count them as one character)
    title = (title or '').replace('\r\n', '\n').strip()
    (link, caption) = ((link or '').strip(), (caption or '').strip())
    if not link or link.lower() == 'https://':
        raise QRSignError('Enter the link for the QR code.')
    if not link.lower().startswith('https://'):
        raise QRSignError('The QR code must be a link starting with https://.')
    try:
        URLValidator(schemes=['https'])(link)
    except ValidationError:
        raise QRSignError('%s isn\'t a valid link.' % link)
    if len(link) > MAX_LINK:
        raise QRSignError('The link can be at most %d characters.' % MAX_LINK)
    if len(title) > MAX_TITLE:
        raise QRSignError('The title can be at most %d characters.' % MAX_TITLE)
    if len(title_lines(title)) > MAX_TITLE_LINES:
        raise QRSignError('The title can have at most %d lines.' % MAX_TITLE_LINES)
    if len(caption) > MAX_CAPTION:
        raise QRSignError('The caption can be at most %d characters.' % MAX_CAPTION)
    return ('\n'.join(title_lines(title)), link, caption or default_caption(link))


def _fit(lines, width, largest):
    """ The largest font size up to largest at which every line fits in
    width (however small that is: lines are never broken). """
    from reportlab.pdfbase.pdfmetrics import stringWidth
    widest = max(stringWidth(line, FONT, 100.0) for line in lines) / 100.0
    if widest <= 0:
        return largest
    return min(largest, width / widest)


def layout(title, link, caption):
    """ The sign as a reportlab Drawing the size of the page; arguments as
    clean() gives them. The title's lines, the code and the caption are each
    as wide as the page allows; if together they're too tall, the text
    shrinks first, down to where the code would get smaller than MIN_CODE. """
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing, Group, String

    (page_width, page_height) = PAGE
    width = page_width - 2 * MARGIN
    lines = title_lines(title)
    title_size = _fit(lines, width, MAX_TITLE_SIZE) if lines else 0
    caption_size = _fit([caption], width, MAX_CAPTION_SIZE)
    caption_lines = [caption]       # (one line, however long)

    def code_side(title_size, caption_size):
        text = (len(lines) * title_size * LINE + GAP if lines else 0) + len(caption_lines) * caption_size * LINE + GAP
        return min(width, page_height - 2 * MARGIN - text)
    def shrink(size):
        return max(min(size, MIN_SIZE), size * 0.95)
    while code_side(title_size, caption_size) < MIN_CODE and max(title_size, caption_size) > MIN_SIZE:
        (title_size, caption_size) = (shrink(title_size), shrink(caption_size))
    side = code_side(title_size, caption_size)

    #   The whole block centered on the page
    block = (len(lines) * title_size * LINE + GAP if lines else 0) + side + GAP + len(caption_lines) * caption_size * LINE
    y = page_height - (page_height - block) / 2
    drawing = Drawing(page_width, page_height)
    for line in lines:
        #   (a line's baseline sits about 0.8 of the font size below its top)
        drawing.add(String(page_width / 2, y - title_size * 0.8, line, fontName=FONT, fontSize=title_size,
                           textAnchor='middle'))
        y -= title_size * LINE
    if lines:
        y -= GAP
    widget = QrCodeWidget(link, barLevel='M', barBorder=0)
    (x1, y1, x2, y2) = widget.getBounds()
    code = Group(widget, transform=[side / (x2 - x1), 0, 0, side / (y2 - y1), (page_width - side) / 2, y - side])
    drawing.add(code)
    y -= side + GAP
    for line in caption_lines:
        drawing.add(String(page_width / 2, y - caption_size * 0.8, line, fontName=FONT, fontSize=caption_size,
                           textAnchor='middle'))
        y -= caption_size * LINE
    return drawing


def sign_pdf(title, link, caption):
    """ The sign as a one-page letter PDF (bytes). """
    from reportlab.graphics import renderPDF
    from reportlab.pdfgen import canvas as pdfcanvas
    out = io.BytesIO()
    c = pdfcanvas.Canvas(out, pagesize=PAGE)
    c.setTitle(' '.join(title_lines(title)) or caption)
    renderPDF.draw(layout(title, link, caption), c, 0, 0)
    c.showPage()
    c.save()
    return out.getvalue()


def sign_svg(title, link, caption):
    """ The sign as SVG, for the page's live preview. """
    from reportlab.graphics import renderSVG
    svg = renderSVG.drawToString(layout(title, link, caption))
    #   Browsers don't know reportlab's font name; Helvetica and Arial share its widths
    svg = svg.replace('font-family="%s"' % FONT, 'font-family="Helvetica, Arial, sans-serif" font-weight="bold"')
    svg = re.sub(r'font-family:\s*%s' % FONT, 'font-family: Helvetica, Arial, sans-serif; font-weight: bold', svg)
    start = svg.find('<svg')
    return svg[start:] if start >= 0 else svg
