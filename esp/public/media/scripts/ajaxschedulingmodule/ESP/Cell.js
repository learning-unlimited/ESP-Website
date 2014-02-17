function Cell(el) {
    this.el = el
    this.el.addClass("matrix-cell")
    this.el.addClass("available-cell")

    this.section = null

    this.removeSection = function(){
	this.section = null
	this.el[0].innerHTML = ""
	this.el.addClass("available-cell")
	this.el.removeClass("occupied-cell")
    }

    this.addSection = function(section){
	this.section = section
	//TODO:  jquery, how am I actually supposed to do this?
	this.el.addClass("occupied-cell")
	this.el.removeClass("available-cell")
	this.el[0].innerHTML = section.emailcode
	this.el.draggable({
	    stack: ".matrix-cell",
	    helper: "clone",
	})
    }

    this.hasSection = function(){
	return this.section != null
    }
}

//TODO:  test that cells have appropriate classes
