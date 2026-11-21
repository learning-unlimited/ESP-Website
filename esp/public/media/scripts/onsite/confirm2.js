/* Two-click confirm. A button with data-confirm="text" (or a function passed to
 * armConfirm) shows the text beside it and relabels to "Confirm" on the first
 * click; a second click within 8 seconds proceeds (submits its form). */
(function ($j) {
    var TIMEOUT = 8000;

    window.armConfirm = function (button, text, onConfirm) {
        var $b = $j(button);
        var state = $b.data('confirm2');
        if (state && state.armed) {
            clearTimeout(state.timer);
            state.disarm();
            if (onConfirm) { onConfirm(); }
            return true;
        }
        var isInput = $b.is('input');
        // Markup, not text, so icons inside the button come back too
        var original = isInput ? $b.val() : $b.html();
        var $msg = $j('<span class="confirm2-text"></span>').text(typeof text === 'function' ? text() : text);
        $b.after($msg);
        $b.addClass('confirm2-armed');
        if (isInput) { $b.val('Confirm'); } else { $b.text('Confirm'); }
        state = {armed: true};
        state.disarm = function () {
            state.armed = false;
            $msg.remove();
            $b.removeClass('confirm2-armed');
            if (isInput) { $b.val(original); } else { $b.html(original); }
        };
        state.timer = setTimeout(state.disarm, TIMEOUT);
        $b.data('confirm2', state);
        return false;
    };

    $j(document).on('click', '[data-confirm]', function (e) {
        var $b = $j(this);
        var text = $b.data('confirm');
        var name = $b.attr('data-confirm-fn');
        if (name && typeof window[name] === 'function') { text = window[name]; }
        var form = this.form;
        e.preventDefault();
        armConfirm(this, text, function () { if (form) { form.submit(); } });
    });
})(window.$j || window.jQuery);
