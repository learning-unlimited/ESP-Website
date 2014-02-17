function Cell(el, section) {
    this.el = el

    this.init = function(new_section){
	if (new_section != null){
	    this.addSection(new_section)
	}
	else{
	    this.removeSection()
	}
	this.el.addClass("matrix-cell")
    }

    this.removeSection = function(){
	this.section = null
	this.el[0].innerHTML = ""
	this.el.addClass("available-cell")
	this.el.droppable({
	    drop:  function(){
		console.log("dropped")
	    }
	})
	this.el.removeClass("occupied-cell")
    }

    this.addSection = function(section){
	this.section = section
	this.el.addClass("occupied-cell")
	this.el.removeClass("available-cell")
	//TODO:  jquery, how am I actually supposed to do this?
	this.el[0].innerHTML = section.emailcode
	this.el.draggable({
	    stack: ".matrix-cell",
	    helper: "clone",
	})
    }

    this.hasSection = function(){
	return this.section != null
    }

    this.init(section)
}

//TODO:  test that cells have appropriate classes
