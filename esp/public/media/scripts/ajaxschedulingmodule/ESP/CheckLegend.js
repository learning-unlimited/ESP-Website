/**
 * Describes what the cell colors mean for the selected scheduling check.
 * The colors here must stay in sync with Cell.cellBackground.
 *
 * @param el: The jquery element to render the legend in.
 * @param matrix: The matrix (used for the class categories).
 *
 * Public methods:
 * @method render(check)
 */
function CheckLegend(el, matrix) {
    this.el = el;
    this.matrix = matrix;
    this.cellColors = new CellColors();

    var cellColors = this.cellColors;

    // Shade used by the checks that count teachers, requests, etc.
    var countColor = function(hue, n) {
        return cellColors.HSLToRGB(hue, 100, 100 - 10 * n);
    };

    // Swatches for counts 0-5+, optionally starting at 1 (with 0 shown as grey)
    var countScale = function(hue, startAtOne) {
        var swatches = [];
        for(var n = startAtOne ? 1 : 0; n <= 5; n++) {
            swatches.push({color: countColor(hue, n), text: n == 5 ? "5+" : String(n)});
        }
        return swatches;
    };

    var gradient = function(from, to) {
        return [{gradient: [from, to]}];
    };

    /**
     * Returns the description and legend entries for each scheduling check.
     * Each entry has a label and a list of swatches (a color or a gradient).
     */
    this.checks = function() {
        return {
            "": {
                description: "Classes are colored by class code; the colors have no other meaning.",
                entries: []
            },
            "capacity": {
                description: "Compares each class's max size to the capacity of its room.",
                entries: [
                    {swatches: gradient(cellColors.HSLToRGB(0, 100, 75), cellColors.HSLToRGB(0, 100, 50)),
                     label: "Room too small (under 50% of class max); darker = smaller room"},
                    {swatches: gradient(cellColors.HSLToRGB(120, 100, 75), cellColors.HSLToRGB(120, 100, 50)),
                     label: "Good fit (50-150% of class max); darker = closer match"},
                    {swatches: gradient(cellColors.HSLToRGB(240, 100, 83), cellColors.HSLToRGB(240, 100, 50)),
                     label: "Room too big (over 150% of class max); darker = bigger room"}
                ]
            },
            "category": {
                description: "Classes are colored by their category.",
                entries: this.categoryEntries()
            },
            "unapproved": {
                description: "Highlights classes that have not been approved.",
                entries: [
                    {swatches: [{color: cellColors.grey}], label: "Approved"},
                    {swatches: [{color: cellColors.red}], label: "Not approved (unreviewed, rejected, or cancelled)"}
                ]
            },
            "requests": {
                description: "Counts the class's resource requests that its room does not provide.",
                entries: [
                    {swatches: [{color: cellColors.grey}], label: "All requests met"},
                    {swatches: countScale(0, true), label: "Number of unmet requests"}
                ]
            },
            "lunch": {
                description: "Highlights classes that cover every lunch block on their day.",
                entries: [
                    {swatches: [{color: cellColors.grey}], label: "Leaves at least one lunch block free"},
                    {swatches: [{color: cellColors.red}], label: "Covers all lunch blocks"}
                ]
            },
            "hungry": {
                description: "Counts the teachers of this class who have no free lunch block on its day.",
                entries: [
                    {swatches: [{color: cellColors.grey}], label: "All teachers get lunch"},
                    {swatches: countScale(0, true), label: "Number of teachers without lunch"}
                ]
            },
            "running": {
                description: "Counts the teachers of this class who teach in a different room directly before or after it.",
                entries: [
                    {swatches: [{color: cellColors.grey}], label: "No teachers changing rooms"},
                    {swatches: countScale(0, true), label: "Number of teachers changing rooms"}
                ]
            },
            "double_booked": {
                description: "Counts the teachers of this class who teach another class at the same time.",
                entries: [
                    {swatches: [{color: cellColors.grey}], label: "No teachers double-booked"},
                    {swatches: countScale(0, true), label: "Number of double-booked teachers"}
                ]
            },
            "unavailable": {
                description: "Shows how many of the class's teachers are unavailable for some or all of it.",
                entries: [
                    {swatches: [{color: cellColors.grey}], label: "All teachers available"},
                    {swatches: gradient(cellColors.HSLToRGB(0, 100, 90), cellColors.HSLToRGB(0, 100, 50)),
                     label: "Some to all teachers unavailable; darker = larger share"}
                ]
            },
            "num_teachers": {
                description: "Shows the number of teachers for each class.",
                entries: [{swatches: countScale(120, false), label: "Number of teachers"}]
            },
            "num_moderators": {
                description: "Shows the number of " + moderator_title.toLowerCase() + "s for each class.",
                entries: [{swatches: countScale(120, false), label: "Number of " + moderator_title.toLowerCase() + "s"}]
            },
            "num_both": {
                description: "Shows the combined number of teachers and " + moderator_title.toLowerCase() + "s for each class.",
                entries: [{swatches: countScale(120, false), label: "Number of teachers and " + moderator_title.toLowerCase() + "s"}]
            },
            "mod_unavailable": {
                description: "Shows how many of the class's " + moderator_title.toLowerCase() + "s are unavailable for some or all of it.",
                entries: [
                    {swatches: [{color: cellColors.grey}], label: "All " + moderator_title.toLowerCase() + "s available"},
                    {swatches: gradient(cellColors.HSLToRGB(0, 100, 90), cellColors.HSLToRGB(0, 100, 50)),
                     label: "Some to all " + moderator_title.toLowerCase() + "s unavailable; darker = larger share"}
                ]
            },
            "mod_cats": {
                description: "Counts the class's " + moderator_title.toLowerCase() + "s who did not select its category on the " + moderator_title.toLowerCase() + " form.",
                entries: [
                    {swatches: [{color: cellColors.grey}], label: "All " + moderator_title.toLowerCase() + "s match"},
                    {swatches: countScale(0, true), label: "Number of " + moderator_title.toLowerCase() + "s with mismatched categories"}
                ]
            }
        };
    };

    /**
     * One entry per class category, colored as in Cell.cellBackground.
     */
    this.categoryEntries = function() {
        var ids = Object.keys(this.matrix.categories);
        return ids.map(function(id, cat_ind) {
            var color = cellColors.hexToRGB(cellColors.colors[Math.round(cat_ind / ids.length * 100)]);
            return {swatches: [{color: color}], label: this.matrix.categories[id].name};
        }.bind(this));
    };

    /**
     * Render the legend for the given scheduling check.
     *
     * @param check: The value of the selected scheduling check radio button.
     */
    this.render = function(check) {
        var info = this.checks()[check];
        this.el.empty();
        if(!info) return;
        this.el.append($j("<p class='check-legend-description'>").text(info.description));
        var table = $j("<table class='check-legend-table'>");
        $j.each(info.entries, function(index, entry) {
            var swatchCell = $j("<td class='check-legend-swatches'>");
            $j.each(entry.swatches, function(index, swatch) {
                swatchCell.append(this.swatch(swatch));
            }.bind(this));
            table.append($j("<tr>").append(swatchCell, $j("<td>").text(entry.label)));
        }.bind(this));
        // Applies regardless of the selected check
        var special = $j("<div class='check-legend-swatch'>").css("background",
            "linear-gradient(to bottom right, " + cellColors.specialColor + " 0%, white 50%, " + cellColors.specialColor + " 100%)");
        table.append($j("<tr>").append($j("<td class='check-legend-swatches'>").append(special),
            $j("<td>").text("Orange corners: class flagged as having special scheduling needs")));
        this.el.append(table);
    };

    /**
     * Create a single swatch element.
     */
    this.swatch = function(swatch) {
        var el = $j("<div class='check-legend-swatch'>");
        if(swatch.gradient) {
            el.addClass("check-legend-gradient").css("background", "linear-gradient(to right, " +
                cellColors.RGBToString(swatch.gradient[0]) + ", " + cellColors.RGBToString(swatch.gradient[1]) + ")");
        } else {
            el.css({"background": cellColors.RGBToString(swatch.color), "color": cellColors.textColor(swatch.color)});
            if(swatch.text) el.text(swatch.text);
        }
        return el;
    };

    /**
     * Add the check descriptions as hover text on the radio button labels.
     */
    this.addHoverText = function() {
        $j.each(this.checks(), function(check, info) {
            $j("label[for='scheduling-checks-" + (check || "none") + "']").attr("title", info.description);
        });
    };

    this.addHoverText();
    this.render("");
}
