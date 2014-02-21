function CellColors() {
    this.color = function(section){
	return "#" + section.emailcode[2] + "0" + section.emailcode[3] + "0" + section.emailcode [4] + "0"
    }
}

function GreenCellColors(){
    this.color = function(section){
	num = section.parent_class
	hex_val = num.toPrecision(6).toString(16).split('.')[0]
	while (hex_val.length < 6) {
	    hex_val = "0" + hex_val
	}
	return "#" + hex_val
    }
}

