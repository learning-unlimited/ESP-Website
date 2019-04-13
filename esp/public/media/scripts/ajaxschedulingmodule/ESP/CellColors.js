/**
 * Controls the color of a cell when it is occuppied by a section
 *
 * Public methods:
 * @method color(section)
 * @method textColor(section)
 */
function CellColors() {
    this.specialColor = "rgb(255, 153, 0)";
    /**
     * Returns the primary background color of the section, as an array of red,
     * green, and blue components.
     *
     * @param section: The section to compute the background color of
     */
    this.color = function(section) {
        var code = section.emailcode;
        var colcode = code.substr(1, code.lastIndexOf("s") - 1).padStart(3, "0");
        return [16*(+colcode.charAt(colcode.length - 3)),
                16*(+colcode.charAt(colcode.length - 2)),
                16*(+colcode.charAt(colcode.length - 1))];
    };
    this.background = function(section) {
        var color = this.color(section);
        var rgb = ("rgb(" +
          color[0] + "," +
          color[1] + "," +
          color[2] + ")");
        if (section.flags.indexOf("Special scheduling needs") !== -1) {
          return ("linear-gradient(to bottom right, " +
            this.specialColor + " 0%," +
            rgb + " 50%," +
            this.specialColor + " 100%)");
        } else {
          return rgb;
        }
    };

    /**
     * Returns the text color of the section (white if dark, black if light)
     *
     * @param section: The section to compute the background color of
     */
    this.textColor = function(section) {
        var color = this.color(section);

        // The relative luminance is a measure of how bright the color is.
        // Green counts more because human eyes are more sensitive to it.
        relativeLuminance = 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2];
        if(relativeLuminance < 128) {
            return "white";
        } else {
            return "black";
        }
    };
}
