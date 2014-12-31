/**
 * The object that initializes and renders all the pieces of the scheduler
 *
 * @param data: The data fetched from the server
 * @param directoryEl: The jquery element that will become the directory
 * @param matrixEl: The jquery element that will become the matrix
 * @param messageEl: The jquery element that will become the message panel
 * @param sectionInfoEl: The jquery element that will become the section info panel
 * @param last_applied_index: The place in the changelog the scheduler is currently at.
 * @param update_interval: The interval in milliseconds between changelog fetches.
 */
function Scheduler(
    data,
    directoryEl,
    matrixEl,
    messageEl,
    sectionInfoEl,
    last_applied_index,
    update_interval
) {
    // Set up all the data and objects
    this.timeslots = new Timeslots(data.timeslots);
    this.rooms = data.rooms;
    this.sections = new Sections(data.sections, 
                                 data.teachers, 
                                 data.schedule_assignments, 
                                 new ApiClient());

    this.messagePanel = new MessagePanel(messageEl, 
                                         "Welcome to the Ajax Scheduler!");
    this.sectionInfoPanel = new SectionInfoPanel(sectionInfoEl, 
                                                 this.sections, 
                                                 this.messagePanel)

    this.matrix = new Matrix(
        this.timeslots,
        this.rooms,
        this.sections,
        matrixEl,
        this.messagePanel,
        this.sectionInfoPanel
    );

    this.directory = new Directory(this.sections, 
                                   directoryEl, 
                                   data.schedule_assignments, 
                                   this.matrix);

    this.changelogFetcher = new ChangelogFetcher(
        this.matrix,
        new ApiClient(),
        last_applied_index
    );


    // set up handlers for selecting and scheduling classes
    $j("body").on("click", "td > a", function(evt, ui) {
        var cell = $j(evt.currentTarget.parentElement).data("cell");
        this.sections.selectSection(cell.section);
    }.bind(this)); 
    $j("body").on("click", "td.teacher-available-cell", function(evt, ui) {
        var cell = $j(evt.currentTarget).data("cell");
        if(this.sections.selectedSection) {
            this.sections.scheduleSection(this.sections.selectedSection, 
                                          cell.room_name, cell.timeslot_id);
        }
    }.bind(this));
    $j("body").on("click", "td.disabled-cell", function(evt, ui) {
        this.sections.unselectSection();
    }.bind(this));


    // Render all the objects on the page
    this.render = function(){
        this.directory.render();
        this.matrix.render();
        this.changelogFetcher.pollForChanges(update_interval);
    };
};
