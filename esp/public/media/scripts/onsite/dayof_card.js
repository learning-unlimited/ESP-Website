/* Onsite card payment buttons (program/modules/dayof/card_pay.html).
 *
 *   DayOfCard.attach(element, {
 *       amount: function () { return dollars; },        // NaN or <= 0: nothing to charge
 *       describe: function (amountText) { return 'Charge $5.00 to a card for ...?'; },  // optional
 *       beforeSubmit: function (form, channel) { ... }   // optional, e.g. set a hidden field
 *   });
 *
 * Shows the card-minimum override when the amount is below the minimum,
 * confirms with two clicks (armConfirm, confirm2.js), and submits the
 * enclosing form: "on this laptop" into a new tab (CyberSource), "on their
 * phone" here (the QR code page). */
(function ($j) {
    window.DayOfCard = {
        attach: function (element, options) {
            var $box = $j(element);
            var form = $box.closest('form')[0];
            var minimum = parseFloat($box.data('card-minimum')) || 0;
            var below = $box.find('.dayof-card-below')[0];
            var override = $box.find('input[name=below_minimum]')[0];
            var reason = $box.find('input[name=below_minimum_reason]')[0];

            function amount() { return options.amount(); }
            function refresh() {
                var a = amount();
                var isBelow = !isNaN(a) && a > 0 && a < minimum;
                below.hidden = !isBelow;
                reason.required = isBelow && override.checked;
                $box.find('.dayof-card-go').prop('disabled', isNaN(a) || a <= 0);
            }
            $j(form).on('input change', refresh);
            refresh();

            $box.on('click', '.dayof-card-go', function () {
                var channel = $j(this).data('channel');
                refresh();
                var a = amount();
                if (isNaN(a) || a <= 0) { return; }
                if (a < minimum && !override.checked) { override.focus(); return; }
                if (!form.checkValidity()) { form.reportValidity(); return; }
                var text = '$' + a.toFixed(2);
                window.armConfirm(this, function () {
                    return options.describe ? options.describe(text) : 'Charge ' + text + ' to a card?';
                }, function () {
                    form.channel.value = channel;
                    if (options.beforeSubmit) { options.beforeSubmit(form, channel); }
                    form.target = channel === 'laptop' ? '_blank' : '';
                    form.submit();
                    form.target = '';
                });
            });
            return {refresh: refresh};
        }
    };
})(window.$j || window.jQuery);
