/**
 * This is a cell that can have class sections assigned to it.
 * Used in the matrix and the directory.
 *
 * @param el: The jquery element that this cell should be rendered on.
 * @param section: The section that should be rendered on this cell (may be null).
 * @param room_id: The ID of the room that corresponds to this cell.
 * @param timeslot_id: The ID of the timeslot that corresponds to this cell.
 * @param matrix: The matrix that created the cell.
 *
 * Public properties and methods:
 * @prop el:
 * @prop cellColors
 * @prop room_id
 * @prop timeslot_id
 * @prop matrix
 * @prop disabled
 *
 * @method select()
 * @method unselect()
 * @method addSection(section)
 * @method removeSection()
 */
function Cell(el, section, room_id, timeslot_id, matrix) {
    this.el = el;

    this.cellColors = new CellColors();
    this.room_id = room_id;
    this.timeslot_id = timeslot_id;
    this.matrix = matrix;
    this.disabled = false;

    this.section = null;
    // Ghost sections are created when you are scheduling a class and hover over a cell
    this.ghostSection = false;
    this.selected = false;


    /**
     * Initialize the cell
     *
     * @param new_section: The section that the cell should be initialized with.
     *                     May be null.
     */
    this.init = function(new_section){
        // Add the cell as data to the element
        this.el.data("cell", this);

        // When cells are occupied, show a tooltip
        $j(this.el).tooltip({
            items: ".occupied-cell",
            content: this.tooltip.bind(this),
            show: {duration: 100},
            hide: {duration: 100},
            track: true,
        });

        // If the cell is initialized with a section, add it.
        if (new_section != null){
            this.addSection(new_section);
        }
        // Otherwise call removeSection to apply the correct styling
        else{
            this.removeSection();
        }
        this.el.addClass("matrix-cell");
    }

    /**
     * Re-apply styling on the cell based on section/selected status.
     */
    this.update = function() {
        this.el.removeData("section");
        this.el.removeClass("available-cell occupied-cell selectable-cell locked-cell selected-section ghost-section");
        this.el[0].innerHTML = "";
        this.el.css("background-color", "");
        this.el.css("background", "");
        this.el.css("color", "");

        if(this.ghostSection || !this.section) {
            this.el.addClass("available-cell");

            if(this.ghostSection) {
                var color = this.cellBackground(this.ghostSection);
                if(this.ghostSection.flags.indexOf("Special scheduling needs") !== -1) {
                    this.el.css("background", "linear-gradient(to bottom right, " + this.cellColors.specialColor + " 0%," +
                        this.cellColors.RGBToString(color) + " 50%," + this.cellColors.specialColor + " 100%)");
                } else {
                    this.el.css("background", this.cellColors.RGBToString(color));
                }
                this.el.css("color", this.cellColors.textColor(color));
                this.el.addClass("ghost-section");
                this.el[0].innerHTML = this.ghostSection.emailcode;
            }
        } else {
            this.el.data("section", this.section);
            this.el.addClass("occupied-cell");
            this.el.addClass("selectable-cell");
            if(this.section.schedulingLocked) {
                this.el.addClass("locked-cell");
            }
            if(this.selected) {
                this.el.addClass("selected-section");
            }
            var color = this.cellBackground(this.section);
            if(this.section.flags.indexOf("Special scheduling needs") !== -1) {
                this.el.css("background", "linear-gradient(to bottom right, " + this.cellColors.specialColor + " 0%," +
                    this.cellColors.RGBToString(color) + " 50%," + this.cellColors.specialColor + " 100%)");
            } else {
                this.el.css("background", this.cellColors.RGBToString(color));
            }
            this.el.css("color", this.cellColors.textColor(color));
            this.el.css("background-size", "cover");
            this.el[0].innerHTML = "<a>" + this.section.emailcode + "</a>";
        }
    };

    this.cellBackground = function(section) {
        var grey = {r: 119, g: 119, b: 119};
        var red = {r: 255, g: 0, b: 0};
        // If this cell is in the directory, always color it normally
        if(!this.room_id) return this.cellColors.color(section);
        // If there is a ghostScheduleAssignment, use that
        if(Object.keys(this.matrix.sections.ghostScheduleAssignment).length > 0){
            var scheduleAssignment = this.matrix.sections.ghostScheduleAssignment;
        } else {
            var scheduleAssignment = this.matrix.sections.scheduleAssignments[section.id];
        }
        switch(this.matrix.scheduling_check) {
            // Color cell based on which scheduling_check is selected
            case "unapproved":
                // Color sections that aren't approved
                if(section.status > 0){
                    return grey;
                } else {
                    return red;
                }
            case "capacity":
                // Color cell based on how well room capacity matches section capacity
                if(this.matrix.rooms[this.room_id].num_students < .5 * section.class_size_max) { // Class size is too big, make cell red
                    return this.cellColors.HSLToRGB(0,100,50 + 50 * (this.matrix.rooms[this.room_id].num_students / section.class_size_max));
                } else if(this.matrix.rooms[this.room_id].num_students > 1.5 * section.class_size_max) { // Class size is too small, make cell blue
                    return this.cellColors.HSLToRGB(240,100,50 + 50 * (section.class_size_max / this.matrix.rooms[this.room_id].num_students));
                } else { // Class size is good, make cell green
                    return this.cellColors.HSLToRGB(120,100,100 - 50 * (Math.min(section.class_size_max, this.matrix.rooms[this.room_id].num_students) / Math.max(section.class_size_max, this.matrix.rooms[this.room_id].num_students)));
                }
            case "category":
                // Color cell based on the class category
                var cat_ind = Object.keys(this.matrix.categories).indexOf(section.category_id.toString());
                return this.cellColors.hexToRGB(this.cellColors.colors[Math.round(cat_ind / Object.keys(this.matrix.categories).length * 100)]);
            case "lunch":
                // Check if section overlaps with all lunch timeslots for a single day
                for(var day in this.matrix.timeslots.lunch_timeslots){
                    var n_overlap = 0;
                    var n_lunch = this.matrix.timeslots.lunch_timeslots[day].length;
                    for(var lunch_timeslot of this.matrix.timeslots.lunch_timeslots[day]){
                        if(scheduleAssignment.timeslots.includes(lunch_timeslot.id)) n_overlap += 1;
                    }
                    if(n_overlap == n_lunch) return red;
                }
                return grey;
            case "requests":
                // Count how many resoure requests are not fulfilled by the room
                var n_req = 0;
                req_loop:
                    for(var req of section.resource_requests[section.id]){
                        for(var res of this.matrix.rooms[this.room_id].associated_resources){
                            if(req[0].id == res.res_type_id && req[1] == res.value) continue req_loop;
                        }
                        n_req += 1;
                        if(n_req == 5) break req_loop;
                    }
                if(n_req == 0) return grey;
                return this.cellColors.HSLToRGB(0,100,100 - 10 * n_req); // Color red based on number of resource requests
            case "hungry":
                // If this section overlaps with lunch, count how many of the coteachers are teaching other sections that overlap with the rest of the lunch time timeslots
                var today = undefined;
                var n_teachers = 0;
                // Find which day, if any, of lunch constraints to worry about (we only care if this section overlaps with lunch at all)
                day_loop:
                    for(var day in this.matrix.timeslots.lunch_timeslots){
                        for(var ts of this.matrix.timeslots.lunch_timeslots[day].map(x => x.id)){
                            if(scheduleAssignment.timeslots.includes(ts)){
                                today = day;
                                break day_loop;
                            }
                        }
                    }
                if(today){
                    // Count how many of the coteachers have sections that overlap with all of the lunch constraints for that day
                    teacher_loop:
                        for(var teacher of section.teacher_data){
                            var lunch_ids = this.matrix.timeslots.lunch_timeslots[today].map(x => x.id);
                            // Address this section separately, since it might be a ghost section (and therefore not in sections.scheduleAssignments)
                            for(var ts of scheduleAssignment.timeslots){
                                if(lunch_ids.includes(ts)){
                                    lunch_ids.splice(lunch_ids.indexOf(ts), 1)
                                }
                                if(lunch_ids.length == 0){
                                    n_teachers += 1;
                                    continue teacher_loop;
                                }
                            }
                            for(var sec of teacher.sections){
                                for(var ts of this.matrix.sections.scheduleAssignments[sec].timeslots){
                                    if(lunch_ids.includes(ts)){
                                        lunch_ids.splice(lunch_ids.indexOf(ts), 1)
                                    }
                                    if(lunch_ids.length == 0){
                                        n_teachers += 1;
                                        continue teacher_loop;
                                    }
                                }
                            }
                        }
                }
                if(n_teachers == 0) return grey;
                return this.cellColors.HSLToRGB(0,100,100 - 10 * n_teachers); // Color red based on number of teachers
            case "double_booked":
                // Count how many of the coteachers are teaching other sections at the same time as this one
                var n_teachers = 0;
                teacher_loop:
                    for(var teacher of section.teacher_data){
                        for(var sec of teacher.sections){
                            if(sec == section.id || !(sec in this.matrix.sections.scheduleAssignments)) continue;
                            for(var ts of this.matrix.sections.scheduleAssignments[sec].timeslots){
                                if(scheduleAssignment.timeslots.includes(ts)){
                                    n_teachers += 1;
                                    continue teacher_loop;
                                }
                            }
                        }
                        if(n_teachers == 5) break teacher_loop;
                    }
                if(n_teachers == 0) return grey;
                return this.cellColors.HSLToRGB(0,100,100 - 10 * n_teachers); // Color red based on number of teachers
            case "running":
                // Count how many of the coteachers are teaching other sections immediately before or after this one in a different room
                var n_teachers = 0;
                teacher_loop:
                    for(var teacher of section.teacher_data){
                        for(var sec of teacher.sections){
                            if(sec == section.id || !(sec in this.matrix.sections.scheduleAssignments)) continue;
                            if(this.matrix.sections.scheduleAssignments[sec].room_id == scheduleAssignment.room_id) continue;
                            for(var ts1 of this.matrix.sections.scheduleAssignments[sec].timeslots){
                                if(scheduleAssignment.timeslots.includes(ts1)) continue;
                                for(var ts2 of scheduleAssignment.timeslots){
                                    if(this.matrix.timeslots.are_timeslots_contiguous([this.matrix.timeslots.get_by_id(ts1), this.matrix.timeslots.get_by_id(ts2)]) ||
                                       this.matrix.timeslots.are_timeslots_contiguous([this.matrix.timeslots.get_by_id(ts2), this.matrix.timeslots.get_by_id(ts1)])){
                                        n_teachers += 1;
                                        continue teacher_loop;
                                    }
                                }
                            }
                        }
                        if(n_teachers == 5) break teacher_loop;
                    }
                if(n_teachers == 0) return grey;
                return this.cellColors.HSLToRGB(0,100,100 - 10 * n_teachers); // Color red based on number of teachers
            case "unavailable":
                // Count how many teachers are not available for some or all of this section
                var n_teachers = 0;
                teacher_loop:
                    for(var teacher of section.teacher_data){
                        for(var ts of scheduleAssignment.timeslots){
                            if(!teacher.availability.includes(ts)){
                                n_teachers += 1;
                                continue teacher_loop;
                            }
                        }
                    }
                if(n_teachers == 0) return grey;
                // Color red based on proportion of unavailable teachers
                return this.cellColors.HSLToRGB(0,100,100 - (n_teachers / section.teacher_data.length) * 50);
            case "num_teachers":
                // Color cell based on the number of teachers for the section
                var n_teachers = Math.min(section.teachers.length, 5)
                return this.cellColors.HSLToRGB(120,100,100 - 10 * n_teachers);
            case "num_moderators":
                // Color cell based on the number of moderators for the section
                var n_moderators = Math.min(section.moderators.length, 5)
                return this.cellColors.HSLToRGB(120,100,100 - 10 * n_moderators);
            case "num_both":
                // Color cell based on the number of teachers and/or moderators for the section
                var n_moderators = Math.min(section.moderators.length + section.teachers.length, 5)
                return this.cellColors.HSLToRGB(120,100,100 - 10 * n_moderators);
            case "mod_unavailable":
                var n_mods = 0;
                mod_loop:
                    for(var moderator of section.moderator_data){
                        for(var ts of scheduleAssignment.timeslots){
                            if(!moderator.availability.includes(ts)){
                                n_mods += 1;
                                continue mod_loop;
                            }
                        }
                    }
                if(n_mods == 0) return grey;
                // Color red based on proportion of unavailable moderators
                return this.cellColors.HSLToRGB(0,100,100 - (n_mods / section.moderator_data.length) * 50);
            case "mod_cats":
                // Color cell based on the number of moderators for the section that have not specified this section's category in the moderator form
                var n_moderators = 0;
                for(var moderator of section.moderator_data){
                    if(!moderator.categories.includes(section.category_id)){
                        n_moderators += 1;
                    }
                }
                return this.cellColors.HSLToRGB(0,100,100 - 10 * n_moderators);
        }
        return this.cellColors.color(section); // Selected scheduling check isn't implemented or none is selected
    };

    /**
     * Highlight a cell and show its info in the section-info panel.
     */
    this.select = function() {
        this.selected = true;
        this.update();
    };

    /**
     * Unhighlight a cell and hide the section-info panel.
     */
    this.unselect = function() {
        this.selected = false;
        this.update();
    };

    /**
     * Create data for the tooltip
     *
     * Note: This has to be bound to the cell for the tooltip jquery function to
     *       work. It would be nice if this was in Sections instead.
     */
    this.tooltip = function(){
        var tooltip_parts = {};
        if(this.section.schedulingComment) {
            tooltip_parts['Scheduling Comment'] = this.section.schedulingComment +
                (this.section.schedulingLocked ? ' <b><i>(locked)</i></b>' : '');
        }
        tooltip_parts['Category'] = this.matrix.categories[this.section.category_id || this.ghostSection.category_id].name;
        tooltip_parts['Teachers'] = this.matrix.sections.getTeachersString(this.section);
        if(has_moderator_module === "True") tooltip_parts[moderator_title + 's'] = this.matrix.sections.getModeratorsString(this.section);
        tooltip_parts['Style'] = this.section.class_style;
        tooltip_parts['Class size max'] = this.section.class_size_max;
        var length_str = '';
        if(Math.floor(this.section.length) > 0){
            length_str += Math.floor(this.section.length);
            length_str += ' hour';
            if(Math.floor(this.section.length) > 1) length_str += 's';
        }
        if((this.section.length % 1) * 60 > 0) length_str += ' ' + Math.round((this.section.length % 1) * 60) + ' minutes';
        tooltip_parts['Length'] = length_str;
        tooltip_parts['Grades'] = this.section.grade_min + "-" + this.section.grade_max;
        tooltip_parts['Room Request'] = this.section.requested_room;
        tooltip_parts['Resource Requests'] = this.matrix.sections.getResourceString(this.section);
        tooltip_parts['Flags'] = this.section.flags;
        if(this.section.comments) {
            tooltip_parts['Comments'] = this.section.comments;
        }
        if(this.section.special_requests && this.section.special_requests.length > 0) {
            tooltip_parts['Room Requests'] = this.section.special_requests;
        }

        var tooltipText = "<b>" + this.section.emailcode + ": " + this.section.title + "</b>";
        for(var header in tooltip_parts) {
            tooltipText += "<br/><b>" + header + "</b>: " + tooltip_parts[header];
        }
        return tooltipText;
    };

    /**
     * Add a section to the cell and update associated data
     *
     * @param section: The section to add to the cell.
     */
    this.addSection = function(section){
        this.section = section;
        this.ghostSection = null;
        this.update();
    };

    /**
     * Remove a section from the cell and all associated data
     */
    this.removeSection = function(){
        this.section = null;
        this.update();
    };

    /**
     * Add a section as a ghost (when scheduling a section and hovering over a cell).
     *
     * @param section: The section to display.
     */
    this.addGhostSection = function(section) {
        this.ghostSection = section;
        this.update();
    };

    /**
     * Remove the ghost section and put back the original section if present.
     */
    this.removeGhostSection = function() {
        this.ghostSection = null;
        this.update();
    };


    this.init(section);
}

/**
 * This is a cell where a room is not available in that time block.
 */
function DisabledCell(el, room_id, timeslot_id) {
    this.room_id = room_id;
    this.timeslot_id = timeslot_id;
    this.el = el;
    this.disabled = true;
    this.init = function(new_section){
        this.el.addClass("matrix-cell");
        this.el.addClass("disabled-cell");
    };

    this.init();
}
