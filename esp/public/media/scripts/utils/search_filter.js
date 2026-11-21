/**
 * Reusable search filter utility for ESP Website.
 * filters elements in a listContainer based on the value of a search input.
 *
 * Elements may carry a data-search-text attribute to be matched on something
 * other than their rendered text (e.g. an identifier that is not displayed).
 *
 * options (optional):
 *   onFilter: function(query, $matched, $elements), run after each filter pass.
 */

window.initSearchFilter = function(inputId, listContainerId, elementSelector, options) {
    var $j = window.jQuery || window.$j;
    if (!$j) {
        console.error("jQuery not found for search filter");
        return;
    }
    options = options || {};

    $j(document).ready(function() {
        var $input = $j("#" + inputId);
        var $container = $j("#" + listContainerId);

        if ($input.length === 0 || $container.length === 0) {
            return;
        }

        function searchText($el) {
            var text = $el.attr("data-search-text");
            return (text === undefined ? $el.text() : text).toLowerCase();
        }

        function filter() {
            var query = ($input.val() || "").trim().toLowerCase();
            var $elements = $container.find(elementSelector);
            var matched = [];

            $elements.each(function() {
                var $el = $j(this);
                if (searchText($el).indexOf(query) > -1) {
                    matched.push(this);
                    $el.show();
                    // If it's a list item, we might want to ensure the parent (like a fieldset row) is visible
                    $el.closest("tr").show();
                } else {
                    $el.hide();
                    // Optional: If all elements in a row are hidden, hide the row
                    // But for simple lists, just hiding the element is fine.
                }
            });

            if (options.onFilter) {
                options.onFilter(query, $j(matched), $elements);
            }
        }

        // "input" rather than "keyup" so paste, autofill, and IME input also filter.
        $input.on("input", _.debounce(filter, 200));
    });
};
