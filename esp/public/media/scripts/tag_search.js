/**
 * Search box for the global and per-program tag settings pages.
 *
 * Row filtering is done by utils/search_filter.js; this script keeps the
 * surrounding collapsible categories in sync: categories with no matching tags
 * are hidden, categories with matches are expanded so the tag is visible, and
 * clearing the box restores whatever the admin had open beforehand.
 */
(function() {
    "use strict";

    var INPUT_ID = "tag-search-input";
    var LIST_ID = "tag-list";
    var ROW_SELECTOR = ".tag-row";

    // expand_display.js expands a category by adding the "active" class and
    // setting an inline max-height (.dspcont is max-height: 0 by default), so
    // set that state directly rather than synthesizing clicks, which would
    // toggle whichever state a category happens to be in.
    function setExpanded(head, expanded) {
        var content = head.nextElementSibling;
        head.classList.toggle("active", expanded);
        if (!content) {
            return;
        }
        content.classList.toggle("active", expanded);
        content.style.maxHeight = expanded ? "none" : "";
    }

    function setVisible(head, visible) {
        var content = head.nextElementSibling;
        head.style.display = visible ? "" : "none";
        if (content) {
            content.style.display = visible ? "" : "none";
        }
    }

    function headsWithMatches($matched) {
        var heads = [];
        $matched.each(function() {
            var content = this.closest(".dspcont");
            var head = content && content.previousElementSibling;
            if (head && heads.indexOf(head) === -1) {
                heads.push(head);
            }
        });
        return heads;
    }

    function describe(count) {
        if (count === 0) {
            return "No tags match your search.";
        }
        return count === 1 ? "1 tag matches your search."
                           : count + " tags match your search.";
    }

    function init() {
        var container = document.getElementById(LIST_ID);
        if (!container || !document.getElementById(INPUT_ID) || !window.initSearchFilter) {
            return;
        }

        var heads = Array.prototype.slice.call(container.querySelectorAll(".dsphead"));
        var status = document.getElementById("tag-search-status");
        var expandedBeforeSearch = null;

        window.initSearchFilter(INPUT_ID, LIST_ID, ROW_SELECTOR, {
            onFilter: function(query, $matched) {
                if (!query) {
                    heads.forEach(function(head, i) {
                        setVisible(head, true);
                        if (expandedBeforeSearch) {
                            setExpanded(head, expandedBeforeSearch[i]);
                        }
                    });
                    expandedBeforeSearch = null;
                    if (status) {
                        status.textContent = "";
                    }
                    return;
                }

                if (!expandedBeforeSearch) {
                    expandedBeforeSearch = heads.map(function(head) {
                        return head.classList.contains("active");
                    });
                }

                var matchedHeads = headsWithMatches($matched);
                heads.forEach(function(head) {
                    var hasMatch = matchedHeads.indexOf(head) !== -1;
                    setVisible(head, hasMatch);
                    setExpanded(head, hasMatch);
                });

                if (status) {
                    status.textContent = describe($matched.length);
                }
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
