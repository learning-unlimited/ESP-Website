/**
 * Controls the color of a cell when it is occupied by a section
 *
 * Public methods:
 * @method color(section)
 * @method textColor(section)
 */
function CellColors() {
    this.colors = palette('tol-rainbow', 100);
    this.specialColor = "rgb(255, 153, 0)";

    this.hexToRGB = function(hex) {
        var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    }

    this.HSLToRGB = function(h,s,l) {
        // Must be fractions of 1
        s /= 100;
        l /= 100;

        let c = (1 - Math.abs(2 * l - 1)) * s,
            x = c * (1 - Math.abs((h / 60) % 2 - 1)),
            m = l - c/2,
            r = 0,
            g = 0,
            b = 0;
        if (0 <= h && h < 60) {
            r = c; g = x; b = 0;  
        } else if (60 <= h && h < 120) {
            r = x; g = c; b = 0;
        } else if (120 <= h && h < 180) {
            r = 0; g = c; b = x;
        } else if (180 <= h && h < 240) {
            r = 0; g = x; b = c;
        } else if (240 <= h && h < 300) {
            r = x; g = 0; b = c;
        } else if (300 <= h && h < 360) {
            r = c; g = 0; b = x;
        }
        r = Math.round((r + m) * 255);
        g = Math.round((g + m) * 255);
        b = Math.round((b + m) * 255);

        return {r: r, g: g, b: b};
    }

    this.RGBToString = function(rgb) {
        return "rgb(" +
              rgb.r + "," +
              rgb.g + "," +
              rgb.b + ")";
    }

    /**
     * Returns the primary background color of the section, as an array of red,
     * green, and blue components.
     *
     * @param section: The section to compute the background color of
     */
    this.color = function(section) {
        var code = section.emailcode;
        var colcode = code.substr(1, code.lastIndexOf("s") - 1).padStart(2, "0");
        /* Use the last two digits of the class code to get a color */
        var col = this.colors[parseInt(colcode.substr(colcode.length - 2)) * 23 % 100];
        return this.hexToRGB(col);
    };

    /**
     * Returns the text color given the rgb color (white if dark, black if light)
     *
     * @param rgb: The rgb background to use to compute text color
     */
    this.textColor = function(rgb) {
        // The relative luminance is a measure of how bright the color is.
        // Green counts more because human eyes are more sensitive to it.
        relativeLuminance = 0.2126 * rgb.r + 0.7152 * rgb.g + 0.0722 * rgb.b;
        if(relativeLuminance < 128) {
            return "white";
        } else {
            return "black";
        }
    };
}
