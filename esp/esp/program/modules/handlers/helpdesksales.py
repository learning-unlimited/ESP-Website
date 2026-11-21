"""Help desk sales: anonymous sales on the day of the program (non-preordered
shirts, plushies, stickers, ...), paid in cash/check or by card, at help
desk prices that can change during the program. Not tied to any account.
Recording a cash sale is optional (only needed for a receipt or if staff
want the record); card sales are always recorded."""
from __future__ import absolute_import
from __future__ import unicode_literals

import json
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils import timezone

from esp.accounting.controllers import ProgramAccountingController
from esp.accounting.models import HelpdeskPriceChange, LineItemType, OnsiteSale, OnsiteSaleLine, Receipt
from esp.program.controllers import dayof, dayof_payments, receipts
from esp.program.modules.base import ProgramModuleObj, needs_onsite, main_call, aux_call
from esp.utils.web import render_to_response


def sellable_items(program):
    """ What the help desk can sell, one entry per (line item, option): every
    optional item (preorder or help-desk-only), at its help desk price. """
    pac = ProgramAccountingController(program)
    #   (get_lineitemtypes_Q leaves out the donation item, which isn't sold)
    items = LineItemType.objects.filter(pac.get_lineitemtypes_Q(include_donations=False), required=False,
                                        for_payments=False).exclude(
        text__in=pac.finaid_items + pac.admission_items).order_by('text', 'id')
    result = []
    for item in items:
        options = list(item.lineitemoptions_set.filter(is_custom=False).order_by('id'))
        if options:
            for option in options:
                result.append({'key': '%d_%d' % (item.id, option.id), 'line_item': item, 'option': option,
                               'label': '%s (%s)' % (item.text, option.description),
                               'price': option.helpdesk_price, 'regular_price': option.amount_dec_inherited,
                               'own_price': option.helpdesk_amount_dec})
        else:
            result.append({'key': '%d_0' % item.id, 'line_item': item, 'option': None, 'label': item.text,
                           'price': item.helpdesk_price, 'regular_price': item.amount_dec,
                           'own_price': item.helpdesk_amount_dec})
    return result


class HelpDeskSales(ProgramModuleObj):
    doc = """Anonymous help desk sales on the day of the program (cash/check or card), with receipts."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Help Desk Sales",
            "link_title": "Help Desk Sales",
            "module_type": "onsite",
            "seq": 6,
            "choosable": 1,
            }

    def _url(self, view='helpdesk_sales'):
        return '/onsite/%s/%s' % (self.program.getUrlBase(), view)

    def _sale(self, request, prog):
        try:
            sale_id = int(request.GET.get('sale') or request.POST.get('sale'))
        except (TypeError, ValueError):
            raise Http404
        sale = OnsiteSale.objects.filter(id=sale_id, program=prog).first()
        if sale is None:
            raise Http404
        return sale

    @main_call
    @needs_onsite
    def helpdesk_sales(self, request, tl, one, two, module, extra, prog):
        if request.method == 'POST':
            return self._create_sale(request, prog)
        since = timezone.now() - timedelta(hours=18)
        recent = OnsiteSale.objects.filter(program=prog, created_at__gte=since).prefetch_related(
            'lines__line_item', 'lines__option', 'receipts').select_related('recorded_by')
        totals = {row['method']: row['total'] for row in OnsiteSale.objects.filter(
            program=prog, status='paid').values('method').annotate(total=Sum('total_dec'))}
        context = {
            'program': prog,
            'items': sellable_items(prog),
            'recent': recent,
            'totals': totals,
            'card_minimum': '%.2f' % dayof_payments.card_minimum(),
            'card_result_text': dayof_payments.result_text(request.GET.get('card_result', '')),
            'focus_sale': OnsiteSale.objects.filter(program=prog, id=request.GET.get('sale') or 0).first()
                if (request.GET.get('sale') or '').isdigit() else None,
            'module': self,
        }
        return render_to_response(self.baseDir() + 'sales.html', request, context)

    def _sale_lines(self, request, prog):
        """ [(entry, quantity)] from the q_<item>_<option> fields. """
        lines = []
        for entry in sellable_items(prog):
            raw = (request.POST.get('q_' + entry['key']) or '').strip()
            if not raw:
                continue
            try:
                quantity = int(raw)
            except ValueError:
                raise ValueError('Quantities must be whole numbers.')
            if quantity < 0:
                raise ValueError('Quantities can\'t be negative.')
            if quantity:
                lines.append((entry, quantity))
        return lines

    def _create_sale(self, request, prog):
        """ Records a sale: 'cash_receipt' (paid cash/check, then show its
        receipt), 'cash' (paid cash/check, no receipt), or 'card' (pending
        until the card payment arrives; channel laptop or qr). """
        action = request.POST.get('action')
        if action not in ('cash_receipt', 'cash', 'card'):
            raise Http404
        try:
            recorded_by = dayof.real_user(request)
            custom = bool(request.POST.get('custom'))
            description = (request.POST.get('description') or '').strip()
            if custom:
                total = dayof.parse_amount(request.POST.get('amount'))
                if total <= 0:
                    raise ValueError('Enter the amount.')
                if not description:
                    raise ValueError('Say what the custom amount is for.')
                lines = []
            else:
                lines = self._sale_lines(request, prog)
                if not lines:
                    raise ValueError('Pick at least one item.')
                total = sum((entry['price'] * quantity for (entry, quantity) in lines), Decimal('0'))
                #   Refuse if prices changed since the page was loaded
                if '%.2f' % total != (request.POST.get('expected_total') or '').strip():
                    raise ValueError('Prices changed since this page was loaded; the total is now %s. '
                                     'Nothing was recorded; please check the items again.' % dayof.money(total))
            with transaction.atomic():
                sale = OnsiteSale.objects.create(
                    program=prog, method='card' if action == 'card' else 'cash_check',
                    status='pending' if action == 'card' else 'paid',
                    payer_name=(request.POST.get('payer_name') or '').strip()[:200],
                    description=description[:200], total_dec=total, recorded_by=recorded_by, paid_at=None if action == 'card' else timezone.now())
                for (entry, quantity) in lines:
                    OnsiteSaleLine.objects.create(sale=sale, line_item=entry['line_item'], option=entry['option'],
                                                  quantity=quantity, unit_price_dec=entry['price'])
                if action == 'card':
                    channel = 'qr' if request.POST.get('channel') == 'qr' else 'laptop'
                    checkout = dayof_payments.sale_checkout(
                        sale, channel, recorded_by,
                        below_minimum_reason=request.POST.get('below_minimum_reason', '')
                        if request.POST.get('below_minimum') else '')
                    page = dayof_payments.checkout_page(
                        request, checkout, status_url='%s?sale=%d' % (self._url('helpdesk_sale_status'), sale.id),
                        back_url='%s?sale=%d' % (self._url(), sale.id), paid_when='sale')
        except ValueError as e:
            messages.error(request, str(e))
            return HttpResponseRedirect(self._url())

        if action == 'cash':
            messages.success(request, 'Recorded a %s cash/check sale (#%d).' % (dayof.money(total), sale.id))
            return HttpResponseRedirect(self._url())
        if action == 'cash_receipt':
            receipt = receipts.create_receipt(prog, receipts.sale_receipt_content(sale), recorded_by,
                                              sale=sale)
            return HttpResponseRedirect('%s?receipt=%d' % (self._url('helpdesk_receipt_view'), receipt.id))
        return page

    def _receipt(self, request, prog):
        try:
            receipt_id = int(request.GET.get('receipt') or request.POST.get('receipt'))
        except (TypeError, ValueError):
            raise Http404
        receipt = Receipt.objects.filter(id=receipt_id, program=prog, sale__isnull=False).first()
        if receipt is None:
            raise Http404
        return receipt

    @aux_call
    @needs_onsite
    def helpdesk_receipt(self, request, tl, one, two, module, extra, prog):
        """ Makes a receipt for a paid sale (optionally with the payer's name). """
        if request.method != 'POST':
            raise Http404
        sale = self._sale(request, prog)
        try:
            recorded_by = dayof.real_user(request)
            content = receipts.sale_receipt_content(sale, (request.POST.get('payer_name') or '').strip())
            receipt = receipts.create_receipt(prog, content, recorded_by, sale=sale)
        except ValueError as e:
            messages.error(request, str(e))
            return HttpResponseRedirect(self._url())
        return HttpResponseRedirect('%s?receipt=%d' % (self._url('helpdesk_receipt_view'), receipt.id))

    @aux_call
    @needs_onsite
    def helpdesk_receipt_view(self, request, tl, one, two, module, extra, prog):
        receipt = self._receipt(request, prog)
        return receipts.receipt_page(request, receipt, {
            'pdf': '%s?receipt=%d' % (self._url('helpdesk_receipt_pdf'), receipt.id),
            'void': self._url('helpdesk_receipt_void'),
            'back': self._url(),
        })

    @aux_call
    @needs_onsite
    def helpdesk_receipt_pdf(self, request, tl, one, two, module, extra, prog):
        return receipts.pdf_response(self._receipt(request, prog))

    @aux_call
    @needs_onsite
    def helpdesk_receipt_void(self, request, tl, one, two, module, extra, prog):
        if request.method != 'POST':
            raise Http404
        receipt = self._receipt(request, prog)
        recorded_by = dayof.real_user(request)
        receipts.void_receipt(receipt, recorded_by)
        messages.success(request, 'Voided receipt %d.' % receipt.number)
        return HttpResponseRedirect(self._url())

    @aux_call
    @needs_onsite
    def helpdesk_sale_status(self, request, tl, one, two, module, extra, prog):
        sale = self._sale(request, prog)
        return HttpResponse(json.dumps({'status': sale.status, 'total': '%.2f' % sale.total_dec,
                                        'transaction_id': sale.transaction_id}),
                            content_type='application/json')

    @aux_call
    @needs_onsite
    def helpdesk_sale_void(self, request, tl, one, two, module, extra, prog):
        """ Voids a mistaken cash sale or an unpaid card sale. A paid card sale
        has to be voided or refunded in CyberSource by treasury. """
        if request.method != 'POST':
            raise Http404
        recorded_by = dayof.real_user(request)
        with transaction.atomic():
            #   Locked, so a card payment arriving right now (which locks it
            #   too) either lands first, and the sale is no longer voidable, or
            #   waits and is flagged for treasury as paid after voiding
            sale = OnsiteSale.objects.select_for_update().get(id=self._sale(request, prog).id)
            if sale.status == 'void':
                messages.error(request, 'Sale #%d was already void.' % sale.id)
            elif sale.status in ('paid', 'review') and sale.method == 'card':
                messages.error(request, 'Sale #%d was paid by card; ask treasury to void or refund it in CyberSource.'
                               % sale.id)
            else:
                sale.status = 'void'
                sale.voided_at = timezone.now()
                sale.voided_by = recorded_by
                sale.save()
                messages.success(request, 'Voided sale #%d (%s).' % (sale.id, dayof.money(sale.total_dec)))
        return HttpResponseRedirect(self._url())

    @aux_call
    @needs_onsite
    def helpdesk_prices(self, request, tl, one, two, module, extra, prog):
        """ The help desk prices, changeable during the program (e.g. raise
        them on the day, or discount leftovers near the end). Each change is
        logged; past sales keep the price they were sold at. """
        if request.method == 'POST':
            try:
                recorded_by = dayof.real_user(request)
                key = request.POST.get('key', '')
                entry = next((e for e in sellable_items(prog) if e['key'] == key), None)
                if entry is None:
                    raise ValueError('Unknown item.')
                raw = (request.POST.get('price') or '').strip()
                new = None if raw == '' else dayof.parse_amount(raw, 'price')
                target = entry['option'] or entry['line_item']
                old = target.helpdesk_amount_dec
                if (request.POST.get('expected_old') or '') != ('' if old is None else '%.2f' % old):
                    raise ValueError('Someone changed that price since this page was loaded; nothing was changed.')
                with transaction.atomic():      # the price and its log entry together
                    target.helpdesk_amount_dec = new
                    target.save()
                    HelpdeskPriceChange.objects.create(program=prog, line_item=entry['line_item'],
                                                       option=entry['option'], old_amount=old, new_amount=new,
                                                       recorded_by=recorded_by)
                messages.success(request, '%s now sells for %s at the help desk.' % (
                    entry['label'], dayof.money(target.helpdesk_price)))
            except ValueError as e:
                messages.error(request, str(e))
            return HttpResponseRedirect(self._url('helpdesk_prices'))
        return render_to_response(self.baseDir() + 'prices.html', request, {
            'program': prog,
            'items': sellable_items(prog),
            'changes': HelpdeskPriceChange.objects.filter(program=prog).select_related(
                'line_item', 'option', 'recorded_by')[:50],
            'module': self,
        })

    class Meta:
        proxy = True
        app_label = 'modules'
