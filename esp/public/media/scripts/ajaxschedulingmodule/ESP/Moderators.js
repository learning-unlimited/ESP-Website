/**
 * This is the directory of moderators that are available to be assigned
 *
 * @param el
 * @param moderators
 * @param matrix
 */
function ModeratorDirectory(el, moderators, matrix) {
    this.el = el;
    this.moderators = moderators;
    this.matrix = matrix;
    this.selectedModerator = null;

    /**
     * Render the directory.
     */
    this.render = function(){
        // Remove old moderators from the directory
        var oldChildren = this.el.children();
        $j.each(oldChildren, function(c){
            oldChildren[c].hidden = true;
        });

        setTimeout(function(){
            $j.each(oldChildren, function(c){
                oldChildren[c].remove();
                });
        }.bind(this), 0);

        // Create the directory table
        var table = $j("<table/>").css("width", "100%");
        $j.each(this.moderators, function(id, moderator){
            var row = new ModeratorRow(moderator, $j("<tr/>"), this);
            row.render();
            row.el.appendTo(table);
        }.bind(this))
        table.appendTo(this.el);
    };

    /**
     * Initialize the direcotry
     */
    this.init = function(){
        // set up handlers
        $j("body").on("schedule-changed", this.render.bind(this));
    }
    this.init();

    /**
     * Bind a matrix to the sections to allow the scheduling methods to work
     *
     * @param matrix: The matrix to bind
     */
    this.bindMatrix = function(matrix) {
        this.matrix = matrix;
    }

    this.selectModerator = function(moderator) {
        if(this.selectedModerator) {
            if(this.selectedModerator === moderator) {
                this.unselectModerator();
                return;
            } else {
                this.unselectModerator();
            }
        }

        // var assignment = this.scheduleAssignments[section.id];
        // if(assignment.room_id) {
            // $j.each(assignment.timeslots, function(index, timeslot) {
                // var cell = this.matrix.getCell(assignment.room_id, timeslot);
                // cell.select();
            // }.bind(this));
        // } else {
            // section.directoryCell.select();
        // }
        this.selectedModerator = moderator;
        this.matrix.sectionInfoPanel.displayModerator(moderator);
        //this.availableTimeslots = this.getAvailableTimeslots(section);
        //this.matrix.highlightTimeslots(this.availableTimeslots, section);
    };

    this.unselectModerator = function(override = false) {
        if(!this.selectedModerator) {
            return;
        }
        // var assignment = this.scheduleAssignments[this.selectedSection.id];
        // if(assignment.room_id) {
            // $j.each(assignment.timeslots, function(index, timeslot) {
                // var cell = this.matrix.getCell(assignment.room_id, timeslot);
                // cell.unselect();
            // }.bind(this));
        // } else {
            // this.selectedSection.directoryCell.unselect();
        // }

        this.selectedModerator = null;
        this.matrix.sectionInfoPanel.hide();
        this.matrix.sectionInfoPanel.override = override;
        //this.matrix.unhighlightTimeslots(this.availableTimeslots);

    };
}

/**
 * This is one row in the directory containing a moderator to be assigned
 *
 * @param moderator: The moderator represented by that row
 * @param el: The element that will form the row
 * @param moderatorDirectory: The moderator directory that contains the row
 *
 * Public methods:
 * @method render()
 * @method hide()
 * @method unHide()
 */
function ModeratorRow(moderator, el, moderatorDirectory){
    this.el = el;
    this.moderator = moderator;
    this.moderatorDirectory = moderatorDirectory;
    this.moderatorCell = new ModeratorCell($j("<td/>"), moderator, moderatorDirectory.matrix);

    /**
     * Style el into a row
     */
    this.render = function(){
        var baseURL = moderatorDirectory.matrix.sections.getBaseUrlString();
        this.el[0].innerHTML = "<td>" + this.moderator.first_name + " " + this.moderator.last_name + 
            " <a target='_blank' href='" + baseURL +
            "edit_availability?user=" + this.moderator.username +
            "'>Edit Availability</a>" + " <a target='_blank' href='/manage/userview?username=" +
            this.moderator.username + "'>Userview</a>" + "</td>";
        this.el.append(this.moderatorCell.el);
    };

    /**
     * Hide the table row
     */
    this.hide = function(){
        this.el.css("display", "none");
    };

    /**
     * Show the table row
     */
    this.unHide = function(){
        this.el.css("display", "table-row");
    };
}

function ModeratorCell(el, moderator, matrix) {
    this.el = el;
    this.moderator = moderator;
    this.matrix = matrix;

    this.init = function() {
        this.el.data("moderatorCell", this);

        $j(this.el).tooltip({
            items: ".moderator-cell",
            content: this.tooltip.bind(this),
            show: {duration: 100},
            hide: {duration: 100},
            track: true,
        });

        this.el.addClass("moderator-cell");
        this.el[0].innerHTML = "<a href='#'>" + this.moderator.id + "</a>";
    }

    this.tooltip = function(){
        var tooltip_parts = {};
        tooltip_parts['Will Moderate'] = (this.moderator.will_moderate)? "Yes" : "No";
        tooltip_parts['Number of Slots'] = this.moderator.num_slots;
        tooltip_parts['Class Categories'] = this.moderator.categories;
        tooltip_parts['Comments'] = this.moderator.comments;

        var tooltipText = "<b>" + this.moderator.first_name + " " + this.moderator.last_name + "</b>";
        for(var header in tooltip_parts) {
            tooltipText += "<br/><b>" + header + "</b>: " + tooltip_parts[header];
        }
        return tooltipText;
    };

    this.init();
}
