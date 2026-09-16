// The admin's FilteredSelectMultiple posts nothing unless the options in its
// "chosen" box are marked selected, which it does from a submit hook of its own.
// elements/html submits with form.submit(), which fires no submit event, so that
// hook never runs here: catch the click first instead, in the capture phase.
(function () {
    function selectChosenOptions(form) {
        if (!form) {
            return;
        }
        form.querySelectorAll('select.filtered[id$="_to"][name]').forEach(function (box) {
            for (const option of box.options) {
                option.selected = true;
            }
        });
    }

    document.addEventListener('click', function (event) {
        const button = event.target.closest && event.target.closest('[type=submit]');
        if (button) {
            selectChosenOptions(button.form || button.closest('form'));
        }
    }, true);

    // Kept for any path that does fire a submit event (e.g. Enter in a text field)
    document.addEventListener('submit', function (event) {
        selectChosenOptions(event.target);
    }, true);
}());
