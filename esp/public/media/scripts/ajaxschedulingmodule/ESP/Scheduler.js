function Scheduler(data, directoryEl, matrixEl, garbageEl) {
    this.directory = new Directory(data.sections, directoryEl, data.schedule_assignments)
    this.matrix = new Matrix(
	data.timeslots,
	data.rooms,
	data.schedule_assignments,
	data.sections,
	matrixEl,
	garbageEl,
	new ApiClient()
    )

    this.render = function(){
	this.directory.render()
	this.matrix.render()

	//turn on tooltips
	$j(document)
	    .tooltip({
		items: ".occupied-cell",
		content: function(){
		    var cell = $j("td:contains("+ this.innerHTML +")").filter(".matrix-cell").first().data("cell")
		    return cell.tooltip()
		}
	    })

    }
}
