/**
 * This is the directory of moderators that are available to be assigned
 *
 * @param el
 * @param moderators
 * @param matrix
 */
function ModeratorDirectory(el, moderators) {
    this.el = el;
    this.moderators = moderators;
    this.selectedModerator = null;
    this.selectedModeratorCell = null;

    // Set up filtering
    this.filter = {
        availMin: {active: false, el: $j("input#mod-filter-avail-min"), type: "number"},
        availMax: {active: false, el: $j("input#mod-filter-avail-max"), type: "number"},
        remainMin: {active: false, el: $j("input#mod-filter-remain-min"), type: "number"},
        remainMax: {active: false, el: $j("input#mod-filter-remain-max"), type: "number"},
        categoryName: {active: false, el: $j("input#mod-filter-category-text"), type: "string"},
    };
    this.filter.availMin.valid = function(a) {
        return a.num_slots >= this.filter.availMin.val;
    }.bind(this);
    this.filter.availMax.valid = function(a) {
        return a.num_slots <= this.filter.availMax.val;
    }.bind(this);
    this.filter.remainMin.valid = function(a) {
        return this.numAvailableSlots(a) >= this.filter.remainMin.val;
    }.bind(this);
    this.filter.remainMax.valid = function(a) {
        return this.numAvailableSlots(a) <= this.filter.remainMax.val;
    }.bind(this);
    this.filter.categoryName.valid = function(a) {
        var result = false;
        $j.each(a.categories, function(index, category) {
            if(this.matrix.sections.categories_data[category].name.toLowerCase().search(this.filter.categoryName.val)>-1) {
                result = true;
            }
        }.bind(this));
        return result;
    }.bind(this);

    $j.each(this.filter, function(filterName, filterObject) {
        filterObject.el.on("change", function() {
            filterObject.val = filterObject.el.val().trim();
            if(filterObject.type==="number") {
                filterObject.val = parseInt(filterObject.val);
            } else if(filterObject.type==="string") {
                filterObject.val = filterObject.val.toLowerCase()
            } else if(filterObject.type==="boolean") {
                filterObject.val = filterObject.el.prop('checked');
            }
            if((filterObject.type==="number" && isNaN(filterObject.val))
                || (filterObject.type==="string" && filterObject.val.trim()==="")
                || (filterObject.type==="boolean" && !filterObject.val)) {
                filterObject.active = false;
            } else {
                filterObject.active = true;
            }
            $j("body").trigger("schedule-changed");
        });
    }.bind(this));

    // Set up search
    this.searchObject = {active: false, text: ""}
    $j("#mod-search-text").on("keyup change", function(evt) {
        this.searchObject.active = evt.currentTarget.value.trim() !== "";
        this.searchObject.text = evt.currentTarget.value;
        $j("body").trigger("schedule-changed");
    }.bind(this));
    
    /**
     * Get the moderators satisfying the search criteria.
     */
    this.filtered_moderators = function(){
        var returned_moderators = [];
        $j.each(this.moderators, function(moderator_id, moderator) {
            var moderatorValid;
            if(this.searchObject.active) {
                // if searchObject is active, ignore searching criteria in the
                // other tab; only filter for moderators that match the
                // searchObject text (note this is a regex match)
                moderatorValid = (moderator.first_name + moderator.last_name).toLowerCase().search(this.searchObject.text.toLowerCase()) > -1;
            } else {
                // if searchObject is not active, check every criterion in the
                // other tab, short-circuiting if possible
                moderatorValid = true;
                for (var filterName in this.filter) {
                    if (this.filter.hasOwnProperty(filterName)) {
                        var filterObject = this.filter[filterName];
                        // this loops over properties in this.filter

                        if (filterObject.active && !filterObject.valid(moderator)) {
                            moderatorValid = false;
                            break;
                        }
                    }
                }
            }

            if (moderatorValid) {
                returned_moderators.push(moderator);
            }
        }.bind(this));
        return returned_moderators;
    };

    // Refresh moderator availability if category match checkbox is changed
    $j("#mod-category-match").on("change", function(evt) {
        if(this.selectedModerator) {
            var moderator = this.selectedModerator;
            this.unselectModerator();
            this.selectModerator(moderator);
        }
    }.bind(this));

    /**
     * Render the moderator directory.
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
        var table = $j("<table/>").css("width", "100%").addClass("sortable");
        table.append($j("<tr/>").append("<th>" + moderator_title + "</th>").append("<th>Available</br>Slots</th>").append("<th>Remaining</br>Slots</th>"));
        $j.each(this.filtered_moderators(), function(id, moderator){
            var row = new ModeratorRow(moderator, $j("<tr/>"), this);
            row.render();
            row.el.appendTo(table);
        }.bind(this))
        table.appendTo(this.el);
        sorttable.makeSortable(table[0]);
    };

    /**
     * Initialize the moderator direcotry
     */
    this.init = function(){
        // set up handlers
        $j("body").on("schedule-changed", this.render.bind(this));
    };
    this.init();

    /**
     * Bind a matrix to the moderator directory to allow the assigning methods to work
     *
     * @param matrix: The matrix to bind
     */
    this.bindMatrix = function(matrix) {
        this.matrix = matrix;
    };

    /**
     * Get a moderator by their ID
     *
     * @param moderator_id: The id of the moderator to get
     */
    this.getById = function(moderator_id) {
        return moderators[moderator_id];
    };

    /**
     * Get the directory cell for a moderator
     *
     * @param moderator: A moderator object
     */
    this.getModeratorCell = function(moderator) {
        return $j("[id='moderator_" + moderator.id + "']").data("moderatorCell");
    };

    /**
     * Calculate a moderator's number of available slots (based on the moderator form and their existing assignments)
     * @param moderator: A moderator object
     */
    this.numAvailableSlots = function(moderator) {
        var avail_slots = moderator.num_slots;
        for(var section of moderator.sections) {
            var assignment = this.matrix.sections.scheduleAssignments[section];
            if(assignment){
                avail_slots -= assignment.timeslots.length;
            }
        }
        return avail_slots;
    };

    /**
     * Get all sections for which a moderator is moderating or teaching
     * @param moderator: A moderator object
     */
    this.getTeachingAndModeratingSections = function(moderator) {
        if(this.matrix.sections.teacher_data[moderator.id]) {
            return Array.from(new Set(this.matrix.sections.teacher_data[moderator.id].sections.concat(moderator.sections)));
        } else {
            return moderator.sections;
        }
    };

    /**
     * Get timeslots for which a moderator is available
     * @param moderator: A moderator object
     */
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

        this.selectedModerator = moderator;
        this.selectedModeratorCell = this.getModeratorCell(moderator);
        this.selectedModeratorCell.el.addClass("selected-moderator");
        this.matrix.sectionInfoPanel.displayModerator(moderator);
        this.availableTimeslots = this.getAvailableTimeslots(moderator);
        this.matrix.highlightTimeslots(this.availableTimeslots, null, moderator);
    };

    this.unselectModerator = function(override = false) {
        if(!this.selectedModerator) {
            return;
        }

        this.matrix.sectionInfoPanel.hide();
        this.matrix.sectionInfoPanel.override = override;
        this.matrix.unhighlightTimeslots(this.availableTimeslots, this.selectedModerator);
        if(this.selectedModeratorCell) {
            this.selectedModeratorCell.el.removeClass("selected-moderator");
            this.selectedModeratorCell = null;
        }
        this.selectedModerator = null;
    };

    /**
     * Assign the selected moderator to the specified section
     * @param section: A section object
     */
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
                this.matrix.messagePanel.addMessage("Error: " + msg, color = "red");
                this.matrix.messagePanel.show();
                console.log(msg);
            }.bind(this)
        );
        // Reset the availability override
        this.matrix.sectionInfoPanel.override = false;
    };

    this.assignModeratorLocal = function(section) {
        var moderator = this.selectedModerator;
        this.unselectModerator();
        if (!section.moderators.includes(moderator.id)) {
            moderator.sections.push(section.id);
            section.moderators.push(moderator.id);
            section.moderator_data.push(moderator);
            $j("body").trigger("schedule-changed");
            this.matrix.messagePanel.addMessage("Success: " + moderator.first_name + " " + moderator.last_name + " was assigned to " + section.emailcode, color = "blue")
            // Update cell coloring
            this.matrix.updateCells();
        }
    };

    /**
     * Unassign the selected moderator from the specified section
     * @param section: A section object
     */
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
                this.matrix.messagePanel.addMessage("Error: " + msg, color = "red")
                console.log(msg);
            }.bind(this)
        );
        // Reset the availability override
        this.matrix.sectionInfoPanel.override = false;
    };

    this.unassignModeratorLocal = function(section) {
        var moderator = this.selectedModerator;
        this.unselectModerator();
        if (section.moderators.includes(moderator.id)) {
            moderator.sections.splice(moderator.sections.indexOf(section.id), 1);
            section.moderators.splice(section.moderators.indexOf(moderator), 1);
            section.moderator_data.splice(section.moderator_data.indexOf(moderator), 1);
            $j("body").trigger("schedule-changed");
            this.matrix.messagePanel.addMessage("Success: " + moderator.first_name + " " + moderator.last_name + " was unassigned from " + section.emailcode, color = "blue")
            // Update cell coloring
            this.matrix.updateCells();
        }
    };
}

/**
 * This is one row in the moderator directory containing a moderator to be assigned
 *
 * @param moderator: The moderator represented by that row
 * @param el: The element that will form the row
 * @param moderatorDirectory: The moderator directory that contains the row
 *
 * Public methods:
 * @method render()
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
}

/**
 * This is the hoverable cell containing the moderator in a moderator row
 *
 * @param moderator: The moderator represented by that row
 * @param el: The element that will form the cell
 * @param matrix: The scheduling matrix
 *
 * Public methods:
 * @method init()
 * @method tooltip()
 */
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
        this.el.attr('id', "moderator_" + this.moderator.id);
        this.el[0].innerHTML = "<td>" + this.moderator.first_name + " " + this.moderator.last_name + 
            "</br><a target='_blank' href='" + baseURL +
            "edit_availability?user=" + this.moderator.username +
            "'>Edit Availability</a>" + " <a target='_blank' href='/manage/userview?username=" +
            this.moderator.username + "&program=" + prog_id + "'>Userview</a>" + "</td>";
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
