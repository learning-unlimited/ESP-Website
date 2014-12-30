function Scheduler(
    data,
    directoryEl,
    matrixEl,
    garbageEl,
    messageEl,
    sectionInfoEl,
    last_applied_index,
    update_interval
) {

    this.matrix = new Matrix(
	    data.timeslots,
	    data.rooms,
        data.teachers,
	    data.schedule_assignments,
	    data.sections,
	    matrixEl,
	    garbageEl,
        new MessagePanel(messageEl, "Welcome to the Ajax Scheduler!"),
        sectionInfoEl,
	    new ApiClient()
    );

    this.directory = new Directory(data.sections, directoryEl, data.schedule_assignments, this.matrix);

    this.changelogFetcher = new ChangelogFetcher(
	this.matrix,
	new ApiClient(),
	last_applied_index
    );

    this.render = function(){
	this.directory.render();
	this.matrix.render();
	this.changelogFetcher.pollForChanges(update_interval);
    };
};
