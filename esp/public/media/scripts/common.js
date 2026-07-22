/* Set up jQuery and shortcuts */
$j = $.noConflict();

$j.getScriptWithCaching = function(url, callback, cache){
// Like getScript, but doesn't do cache busting
$j.ajax({
        type: "GET",
        url: url,
        success: callback,
        dataType: "script",
        cache: true
});
};

$j(document).on('focusin', 'input[type=number]', function() {
        $j(this).on('wheel mousewheel DOMMouseScroll.numberInputBlur', function() {
                this.blur();
        });
});

$j(document).on('focusout', 'input[type=number]', function() {
        $j(this).off('wheel.numberInputBlur mousewheel.numberInputBlur DOMMouseScroll.numberInputBlur');
});
