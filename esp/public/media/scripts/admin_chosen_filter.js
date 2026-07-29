// Add a filter input to the "Chosen" panel of filter_horizontal widgets.
// Patched in hackily: deferred via setTimeout so it runs after SelectFilter2.js's own window.load
// handler has finished building the widget DOM.
//
// Deliberately does NOT use SelectBox.filter (which the available panel uses): that rebuilds
// the <select> from its cache and drops non-matching <option>s from the DOM entirely. On the
// chosen panel that's fatal, because SelectFilter2's submit handler (SelectBox.select_all) only
// marks options currently present in the DOM as selected — anything hidden by the filter is
// silently excluded from the submitted value, and if the filter matches nothing the field
// submits empty, tripping the "at least one value must be selected" validation error even
// though items are actually chosen. Hiding options via CSS instead keeps them in the DOM (and
// thus in the submitted value) regardless of filter text.
function filterChosenOptions(select_id, text) {
    var select = document.getElementById(select_id);
    if (!select) {
        return;
    }
    var tokens = text.toLowerCase().split(/\s+/).filter(Boolean);
    Array.prototype.forEach.call(select.options, function(option) {
        var option_text = option.text.toLowerCase();
        var visible = tokens.every(function(token) {
            return option_text.indexOf(token) !== -1;
        });
        option.style.display = visible ? '' : 'none';
    });
}

window.addEventListener('load', function() {
    setTimeout(function() {
        document.querySelectorAll('.selector-chosen select.filtered').forEach(function(to_box) {
            var field_id = to_box.id.replace(/_to$/, '');
            var input_id = field_id + '_to_input';

            // Mirror the structure SelectFilter2.js builds for the available panel.
            var filter_p = document.createElement('p');
            filter_p.className = 'selector-filter';
            filter_p.id = field_id + '_to_filter';

            var label = document.createElement('label');
            label.setAttribute('for', input_id);
            var icon = document.createElement('span');
            icon.className = 'help-tooltip search-label-icon';
            icon.setAttribute('title', gettext('Type into this box to filter down the list of chosen items.'));
            label.appendChild(icon);
            filter_p.appendChild(label);
            filter_p.appendChild(document.createTextNode(' '));

            var filter_input = document.createElement('input');
            filter_input.type = 'text';
            filter_input.id = input_id;
            filter_input.placeholder = gettext('Filter');
            filter_p.appendChild(filter_input);

            to_box.parentNode.insertBefore(filter_p, to_box);

            filter_input.addEventListener('keyup', function() {
                filterChosenOptions(field_id + '_to', filter_input.value);
            });
        });
    }, 0);
});
