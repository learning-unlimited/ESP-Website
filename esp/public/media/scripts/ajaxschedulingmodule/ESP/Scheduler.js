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
    sectionDialogEl,
    last_applied_index,
    update_interval
) {
    // Set up all the data and objects

    // Populate data with resources
    $j.each(data.rooms, function(index, room) {
        room.resources = [];
        room.resource_lines = [];
        $j.each(room.associated_resources, function(index, resource) {
            var resource_type = data.resource_types[resource.res_type_id];
            room.resources.push({
                'resource_type': resource_type,
                'value': resource.value,
            });
            var desc = resource_type.name;
            if(resource.value) {
                desc += ': ' + resource.value;
            }
            room.resource_lines.push(desc);
        });
    });

    $j.each(data.sections, function(index, section) {
        requests = section.resource_requests[section.id];
        if(requests) {
            $j.each(requests, function(index, resource_array) {
                resource_array[0] = data.resource_types[resource_array[0]];
            });
        } else {
            section.resource_requests = {};
            section.resource_requests[section.id] = [];
        }


    });

    this.lunch_timeslots = data.lunch_timeslots;
    this.timeslots = new Timeslots(data.timeslots, this.lunch_timeslots);

    this.rooms = data.rooms;

    this.sections = new Sections(data.sections,
                                 data.section_details,
                                 data.teachers,
                                 data.schedule_assignments,
                                 new ApiClient());

    this.messagePanel = new MessagePanel(messageEl,
                                         "Welcome to the Ajax Scheduler!");
    this.sectionCommentDialog = new SectionCommentDialog(sectionDialogEl, this.sections);
    this.sectionInfoPanel = new SectionInfoPanel(sectionInfoEl,
                                                 this.sections,
                                                 this.messagePanel,
                                                 this.sectionCommentDialog)

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


    // Set up keyboard shortcut for unscheduling
    $j("body").keydown(function(evt) {
        console.log(evt);
        if(evt.keyCode == 46) { // delete is pressed
            this.sections.unscheduleSection(this.sections.selectedSection);
        } else if(evt.keyCode == 27) { // escape is pressed
            this.sections.unselectSection()
        } else if(evt.keyCode == 112) { // F1 is pressed
            evt.preventDefault();
            $j("#side-panel").tabs({active: 0});
        } else if(evt.keyCode == 113) { // F3 is pressed
            evt.preventDefault();
            $j("#side-panel").tabs({active: 1});
        }
    }.bind(this));

    $j('body').keyup(function(evt) {
        if(evt.keyCode == 191) { // '/' is pressed
            $j("#side-panel").tabs({active: 0});
            $j("#class-search-text").focus();
        }
    });


    // set up handlers for selecting and scheduling classes
    $j("body").on("click", "td.matrix-cell > a", function(evt, ui) {
        var cell = $j(evt.currentTarget.parentElement).data("cell");
        this.sections.selectSection(cell.section);
    }.bind(this));

    $j("body").on("mouseleave click", "td.teacher-available-cell", function(evt, ui) {
        this.sections.unscheduleAsGhost();
    }.bind(this));

    $j("body").on("click", "td.teacher-available-cell", function(evt, ui) {
        var cell = $j(evt.currentTarget).data("cell");
        if(this.sections.selectedSection) {
            this.sections.scheduleSection(this.sections.selectedSection,
                                          cell.room_id, cell.timeslot_id);
        }
    }.bind(this));

    $j("body").on("click", "td.disabled-cell", function(evt, ui) {
        this.sections.unselectSection();
    }.bind(this));

   $j("body").on("mouseenter", "td.teacher-available-cell", function(evt, ui) {
        var cell = $j(evt.currentTarget).data("cell");
        this.sections.scheduleAsGhost(cell.room_id, cell.timeslot_id);
    }.bind(this));

    // Render all the objects on the page
    this.render = function(){
        this.directory.render();
        this.matrix.render();
        this.changelogFetcher.pollForChanges(update_interval);
    };
};
