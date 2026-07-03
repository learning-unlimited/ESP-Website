/**
 * Reusable search filter utility for ESP Website.
 * filters elements in a listContainer based on the value of a search input.
 */

window.initSearchFilter = function(inputId, listContainerId, elementSelector) {
    var $j = window.jQuery || window.$j;
    if (!$j) {
        console.error("jQuery not found for search filter");
        return;
    }

    $j(document).ready(function() {
        var $input = $j("#" + inputId);
        var $container = $j("#" + listContainerId);

        if ($input.length === 0 || $container.length === 0) {
            return;
        }

        $input.on("keyup", _.debounce(function() {
            var query = $input.val().toLowerCase();
            var $elements = $container.find(elementSelector);

            $elements.each(function() {
                var $el = $j(this);
                var text = $el.text().toLowerCase();
                if (text.indexOf(query) > -1) {
                    $el.show();
                    // If it's a list item, we might want to ensure the parent (like a fieldset row) is visible
                    $el.closest("tr").show();
                } else {
                    $el.hide();
                    // Optional: If all elements in a row are hidden, hide the row
                    // But for simple lists, just hiding the element is fine.
                }
            });
        }, 200));
    });
};
