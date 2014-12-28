// Changes the color of a cell.

function CellColors() {
    this.color = function(section){
	    return "#" + section.emailcode[2] + "0" + section.emailcode[3] + "0" + section.emailcode [4] + "0";
    };
    this.textColor = function(section) {
        var color = helpers_hex_string_to_color(this.color(section));
        relativeLuminance = 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2];
        if(relativeLuminance < 128) {
            return "white";
        } else {
            return "black";
        }
    };
}

function GreenCellColors(){
    this.color = function(section){
	    var num = section.parent_class;
	    var hex_val = num.toPrecision(6).toString(16).split('.')[0];
	    while (hex_val.length < 6) {
	        hex_val = "0" + hex_val;
	    }
	    return "#" + hex_val;
    };
}

