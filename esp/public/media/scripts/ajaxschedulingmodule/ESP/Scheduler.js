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

    this.messagePanel = new MessagePanel(messageEl, "Welcome to the Ajax Scheduler!");
    this.matrix = new Matrix(
	    new Timeslots(data.timeslots),
	    data.rooms,
	    new Sections(data.sections, data.teachers, data.schedule_assignments, new ApiClient()),
	    matrixEl,
	    garbageEl,
        this.messagePanel,
        new SectionInfoPanel(sectionInfoEl, data.teachers, this.messagePanel)
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
