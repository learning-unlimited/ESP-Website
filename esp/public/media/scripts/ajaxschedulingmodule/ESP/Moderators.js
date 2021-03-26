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
        table.append($j("<tr/>").append("<th>Moderator</th>").append("<th>Available</br>Slots</th>").append("<th>Remaining</br>Slots</th>"));
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
    };
    this.init();

    /**
     * Bind a matrix to the sections to allow the scheduling methods to work
     *
     * @param matrix: The matrix to bind
     */
    this.bindMatrix = function(matrix) {
        this.matrix = matrix;
    };

    this.numAvailableSlots = function(moderator) {
        var avail_slots = moderator.num_slots;
        for(section of moderator.sections) {
            var assignment = this.matrix.sections.scheduleAssignments[section]
            if(assignment){
                avail_slots -= assignment.timeslots.length;
            }
        }
        return avail_slots;
    };

    this.getTeachingAndModeratingSections = function(moderator) {
        if(this.matrix.sections.teacher_data[moderator.id]) {
            return Array.from(new Set(this.matrix.sections.teacher_data[moderator.id].sections.concat(moderator.sections)));
        } else {
            return moderator.sections;
        }
    };

    this.getAvailableTimeslots = function(moderator) {
        var availableTimeslots = [];
        var already_teaching = [];
        if(this.matrix.sectionInfoPanel.override){
            $j.each(this.matrix.timeslots.timeslots, function(index, timeslot) {
                availableTimeslots.push(timeslot.id);
            }.bind(this));
        } else {
            var availableTimeslots = moderator.availability.slice();
            availableTimeslots = availableTimeslots.filter(function(val) {
                return this.matrix.timeslots.get_by_id(val);
            }.bind(this));
            // get when the moderator is teaching or moderating
            $j.each(this.getTeachingAndModeratingSections(moderator), function(index, section_id) {
                var assignment = this.matrix.sections.scheduleAssignments[section_id];
                if(assignment) {
                    $j.each(assignment.timeslots, function(index, timeslot_id) {
                        var availability_index = availableTimeslots.indexOf(timeslot_id);
                        if(availability_index >= 0) {
                            availableTimeslots.splice(availability_index, 1);
                            already_teaching.push(timeslot_id);
                        }
                    }.bind(this));
                }
            }.bind(this));
        }
        return [availableTimeslots, already_teaching];
    };

    this.selectModerator = function(moderator) {
        if(this.matrix.sections.selectedSection) {
            this.matrix.sections.unselectSection();
        }
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
        this.availableTimeslots = this.getAvailableTimeslots(moderator);
        this.matrix.highlightTimeslots(this.availableTimeslots, null, moderator);
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

        this.matrix.sectionInfoPanel.hide();
        this.matrix.sectionInfoPanel.override = override;
        this.matrix.unhighlightTimeslots(this.availableTimeslots, this.selectedModerator);
        this.selectedModerator = null;
    };

    this.assignModerator = function(section) {
        var override = this.matrix.sectionInfoPanel.override;
        this.matrix.sections.apiClient.assign_moderator(
            section.id,
            this.selectedModerator.id,
            override,
            function() {
                // If successful, update moderator info
                this.assignModeratorLocal(section);
            }.bind(this),
            function(msg) {
                // If unsuccessful, report the error message
                this.matrix.messagePanel.addMessage("Error: " + msg)
                console.log(msg);
            }.bind(this)
        );
        // Reset the availability override
        this.matrix.sectionInfoPanel.override = false;
    };

    this.assignModeratorLocal = function(section) {
        moderator = this.selectedModerator;
        this.unselectModerator();
        moderator.sections.push(section.id);
        section.moderators.push(moderator.id);
        section.moderator_data.push(moderator);
        $j("body").trigger("schedule-changed");
    };

    this.unassignModerator = function(section) {
        this.matrix.sections.apiClient.unassign_moderator(
            section.id,
            this.selectedModerator.id,
            function() {
                // If successful, update moderator info
                this.unassignModeratorLocal(section);
            }.bind(this),
            function(msg) {
                // If unsuccessful, report the error message
                this.matrix.messagePanel.addMessage("Error: " + msg)
                console.log(msg);
            }.bind(this)
        );
        // Reset the availability override
        this.matrix.sectionInfoPanel.override = false;
    };

    this.unassignModeratorLocal = function(section) {
        moderator = this.selectedModerator;
        this.unselectModerator();
        moderator.sections.splice(moderator.sections.indexOf(section.id), 1);
        section.moderators.splice(section.moderators.indexOf(moderator), 1);
        section.moderator_data.splice(section.moderator_data.indexOf(moderator), 1);
        $j("body").trigger("schedule-changed");
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
        this.el.append(this.moderatorCell.el);
        this.el.append($j("<td>" + moderator.num_slots + "</td>").addClass("num-avail").css("text-align", "center"));
        this.el.append($j("<td>" + this.moderatorDirectory.numAvailableSlots(moderator) + "</td>").addClass("num-remain").attr("id", "num-remain-" + moderator.id).css("text-align", "center")); // need to calculate how many slots are still available
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
        var baseURL = this.matrix.sections.getBaseUrlString();
        this.el[0].innerHTML = this.el[0].innerHTML = "<td>" + this.moderator.first_name + " " + this.moderator.last_name + 
            "</br><a target='_blank' href='" + baseURL +
            "edit_availability?user=" + this.moderator.username +
            "'>Edit Availability</a>" + " <a target='_blank' href='/manage/userview?username=" +
            this.moderator.username + "'>Userview</a>" + "</td>";
    }

    this.tooltip = function(){
        var tooltip_parts = {};
        tooltip_parts['Will Moderate'] = (this.moderator.will_moderate)? "Yes" : "No";
        tooltip_parts['Number of Slots'] = this.moderator.num_slots;
        tooltip_parts['Class Categories'] = this.moderator.categories.map(cat => this.matrix.categories[cat].name).join(', ');
        tooltip_parts['Comments'] = this.moderator.comments;

        var tooltipText = "<b>" + this.moderator.first_name + " " + this.moderator.last_name + "</b>";
        for(var header in tooltip_parts) {
            tooltipText += "<br/><b>" + header + "</b>: " + tooltip_parts[header];
        }
        return tooltipText;
    };

    this.init();
}