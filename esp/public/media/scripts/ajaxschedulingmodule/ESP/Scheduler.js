function Scheduler(data, directoryEl, matrixEl, garbageEl, last_applied_index) {
    this.directory = new Directory(data.sections, directoryEl, data.schedule_assignments);
    this.matrix = new Matrix(
	data.timeslots,
	data.rooms,
	data.schedule_assignments,
	data.sections,
	matrixEl,
	garbageEl,
	new ApiClient()
    );

    this.changelogFetcher = new ChangelogFetcher(
	this.matrix,
	new ApiClient(),
	//TODO:  update to configurable values
	10,
	last_applied_index,
	data.sections
    );

    this.render = function(){
	this.directory.render();
	this.matrix.render();
	this.changelogFetcher.pollForChanges();
    };
};
