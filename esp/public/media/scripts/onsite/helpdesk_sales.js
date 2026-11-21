/* Help desk sales page: quantity steppers, running total, two-click confirmed
 * cash/check buttons, and the card buttons (dayof_card.js). */
(function ($j) {
    function money(n) { return n.toFixed(2); }

    function parseCents(text) {
        var m = /^\s*\$?\s*(\d+)(?:\.(\d{1,2}))?\s*$/.exec(text || '');
        if (!m) { return 0; }
        return parseInt(m[1], 10) * 100 + parseInt(((m[2] || '') + '00').substr(0, 2), 10);
    }

    $j(function () {
        var $form = $j('#hd-form');
        if (!$form.length) { return; }
        var state = {cents: 0, count: 0};

        function recompute() {
            var cents = 0, count = 0;
            if ($j('#hd-custom').is(':checked')) {
                cents = parseCents($j('#hd-amount').val());
                count = 1;
            } else {
                $j('.hd-q').each(function () {
                    var q = parseInt($j(this).val(), 10);
                    if (q > 0) {
                        cents += q * parseCents($j(this).data('price'));
                        count += q;
                    }
                });
            }
            state.cents = cents; state.count = count;
            $j('#hd-total-num').text(money(cents / 100));
            $j('#hd-expected').val(money(cents / 100));
            $j('.hd-submit').prop('disabled', cents <= 0);
        }

        $form.on('input change', 'input', recompute);
        $form.on('click', '.hd-plus, .hd-minus', function () {
            var $q = $j(this).closest('.hd-qty').find('.hd-q');
            var q = parseInt($q.val(), 10) || 0;
            q = Math.max(0, q + ($j(this).hasClass('hd-plus') ? 1 : -1));
            $q.val(q ? q : '');
            recompute();
        });

        function describe(action) {
            var total = '$' + money(state.cents / 100);
            var custom = $j('#hd-custom').is(':checked');
            var what = custom ? 'custom amount' : state.count + (state.count === 1 ? ' item' : ' items');
            return 'Record ' + total + ' cash/check sale (' + what + ')' +
                (action === 'cash_receipt' ? ' with receipt?' : ', no receipt?');
        }

        $form.on('click', '.hd-submit', function () {
            var action = $j(this).data('action');
            var form = $form[0];
            form.target = '';
            recompute();
            if (state.cents <= 0) { return; }
            window.armConfirm(this, function () { return describe(action); }, function () {
                $j('#hd-action').val(action);
                form.submit();
            });
        });

        recompute();
        window.DayOfCard.attach($form.find('.dayof-card-pay'), {
            amount: function () { recompute(); return state.cents / 100; },
            describe: function (amount) {
                var what = $j('#hd-custom').is(':checked') ? 'custom amount'
                    : state.count + (state.count === 1 ? ' item' : ' items');
                return 'Charge ' + amount + ' to a card (' + what + ')?';
            },
            beforeSubmit: function (f) { $j('#hd-action').val('card'); }
        });
    });
})(window.$j || window.jQuery);
