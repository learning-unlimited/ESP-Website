/**
 * Controls the color of a cell when it is occuppied by a section
 *
 * Public methods:
 * @method color(section)
 * @method textColor(section)
 */
function CellColors() {
    /**
     * Returns the background color of the section.
     *
     * @param section: The section to compute the background color of
     */
    this.color = function(section){
 	    return "#" + 
            section.emailcode[2] + "0" + 
            section.emailcode[3] + "0" + 
            section.emailcode [4] + "0";
    };

    /**
     * Returns the text color of the section (white if dark, black if light)
     *
     * @param section: The section to compute the background color of
     */
    this.textColor = function(section) {
        var color = helpers_hex_string_to_color(this.color(section));
        
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

