/**
 * Stores the section data and provides helper methods for accessing and scheduling
 * sections.
 *
 * @params sections_data: The raw section data
 * @params section_details_data: The AJAX section detail data
 * @params teacher_data: The raw teacher data for populating the sections
 * @params scheduleAssignments: The scheule assignments
 * @params apiClient: The object that can communicate with the server
 */
function Sections(sections_data, section_details_data, teacher_data, scheduleAssignments, apiClient) {
    this.sections_data = sections_data;
    this.scheduleAssignments = scheduleAssignments;
    this.apiClient = apiClient;

    // The section that is currently selected
    this.selectedSection = null;
    this.ghostScheduleAssignment = {};
    this.availableTimeslots = [];

    // Set up filtering
    this.filter = {
        classLengthMin: {active: false, el: $j("input#section-filter-length-min"), type: "number"},
        classLengthMax: {active: false, el: $j("input#section-filter-length-max"), type: "number"},
        classCapacityMin: {active: false, el: $j("input#section-filter-capacity-min"), type: "number"},
        classCapacityMax: {active: false, el: $j("input#section-filter-capacity-max"), type: "number"},
        gradeMin: {active: false, el: $j("input#section-filter-grade-min"), type: "number"},
        gradeMax: {active: false, el: $j("input#section-filter-grade-max"), type: "number"},
        classTeacher: {active: false, el: $j("input#section-filter-teacher-text"), type: "string"},
        classHideUnapproved: {active: false, el: $j("input#section-filter-unapproved"), type: "boolean"},
        classHasAdmin: {active: false, el: $j("input#section-filter-admin"), type: "boolean"},
        classFlags: {active: false, el: $j("input#section-filter-flags-text"), type: "string"},
        classResources: {active: false, el: $j("input#section-filter-resources-text"), type: "string"},
    };
    this.filter.classLengthMin.valid = function(a) {
        return Math.ceil(a.length) >= this.filter.classLengthMin.val;
    }.bind(this);
    this.filter.classLengthMax.valid = function(a) {
        return Math.ceil(a.length) <= this.filter.classLengthMax.val;
    }.bind(this);
    this.filter.classCapacityMin.valid = function(a) {
        return a.class_size_max >= this.filter.classCapacityMin.val;
    }.bind(this);
    this.filter.classCapacityMax.valid = function(a) {
        return a.class_size_max <= this.filter.classCapacityMax.val;
    }.bind(this);
    this.filter.gradeMin.valid = function(a) {
        return a.grade_min == this.filter.gradeMin.val;
    }.bind(this);
    this.filter.gradeMax.valid = function(a) {
        return a.grade_max == this.filter.gradeMax.val;
    }.bind(this);
    this.filter.classTeacher.valid = function(a) {
        var result = false;
        $j.each(a.teacher_data, function(index, teacher) {
            if((teacher.first_name + teacher.last_name).toLowerCase().search(this.filter.classTeacher.val)>-1) {
                result = true;
            }
        }.bind(this));
        return result;
    }.bind(this);
    this.filter.classHasAdmin.valid = function(a) {
        var result = false;
        $j.each(a.teacher_data, function(index, teacher) {
            if(teacher.is_admin) {
                result = true;
            }
        }.bind(this));
        return result;
    }.bind(this);
    this.filter.classHideUnapproved.valid = function(a) {
        return a.status > 0;
    }.bind(this);
    this.filter.classFlags.valid = function(a) {
        return a.flags.toLowerCase().search(this.filter.classFlags.val)>-1;
    }.bind(this);
    this.filter.classResources.valid = function(a) {
        return this.getResourceString(a).toLowerCase().search(this.filter.classResources.val)>-1;
    }.bind(this);

    $j.each(this.filter, function(filterName, filterObject) {
        filterObject.el.change(function() {
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
    this.searchObject = {active: false, text: "", type: $j("[name='class-search-type']").val()}
    $j("#class-search-text, [name='class-search-type']").on("keyup change", function(evt) {
        if(evt.currentTarget.id === "class-search-text") {
            this.searchObject.active = evt.currentTarget.value.trim() !== "";
            this.searchObject.text = evt.currentTarget.value;
        } else {
            this.searchObject.type = evt.currentTarget.value;
        }
        $j("body").trigger("schedule-changed");
    }.bind(this));


    /**
     * Populate the sections data with teacher and section-detail info
     */
    this.init = function() {
        $j.each(sections_data, function(section_id, section) {
            section.teacher_data = []
            $j.each(section.teachers, function(index, teacher_id) {
                section.teacher_data.push(teacher_data[teacher_id]);
            });

            sectionDetails = section_details_data[section_id];
            if(sectionDetails) {
                section.schedulingComment = sectionDetails[0].comment;
                section.schedulingLocked = sectionDetails[0].locked;
            } else {
                section.schedulingComment = '';
                section.schedulingLocked = false;
            }
        });
    };

    this.init();

    /**
     * Bind a matrix to the sections to allow the scheduling methods to work
     *
     * @param matrix: The matrix to bind
     */
    this.bindMatrix = function(matrix) {
        this.matrix = matrix;
    }

    /**
     * Get a section by its ID
     *
     * @param section_id: The id of the section to get
     */
    this.getById = function(section_id) {
        return sections_data[section_id];
    };

    /**
     * Whether the specified section is scheduled
     */
    this.isScheduled = function(section) {
        return this.scheduleAssignments[section.id] &&
            this.scheduleAssignments[section.id].room_id;
    };

    /**
     * Get the sections satisfying the search criteria. By default, filter
     * out sections that have been scheduled.
     */
    this.filtered_sections = function(allowScheduled){
        var returned_sections = [];
        $j.each(this.sections_data, function(section_id, section) {
            if (!this.scheduleAssignments[section.id]) {
                // filter out rejected sections
                return;
            }
            if (this.isScheduled(section) && !allowScheduled) {
                // filter out scheduled sections
                return;
            }
            var sectionValid;
            if(this.searchObject.active) {
                // if searchObject is active, ignore searching criteria in the
                // other tab; only filter for sections that match the
                // searchObject text (note this is a regex match)
                sectionValid = (
                    section[this.searchObject.type].toLowerCase()
                    .search(this.searchObject.text.toLowerCase()) > -1
                );
            } else {
                // if searchObject is not active, check every criterion in the
                // other tab, short-circuiting if possible
                sectionValid = true;
                for (var filterName in this.filter) {
                    if (this.filter.hasOwnProperty(filterName)) {
                        var filterObject = this.filter[filterName];
                        // this loops over properties in this.filter

                        if (filterObject.active && !filterObject.valid(section)) {
                            sectionValid = false;
                            break;
                        }
                    }
                }
            }

            if (sectionValid) {
                returned_sections.push(section);
            }
        }.bind(this));
        return returned_sections;
    };

    /**
     * Select the cells associated with this section, put it on the section info
     * panel, and highlight the available cells to place the section.
     *
     * @param section: The section to select
     */
    this.selectSection = function(section) {
        if(this.selectedSection) {
            if(this.selectedSection === section) {
                this.unselectSection();
                return;
            } else {
                this.unselectSection();
            }
        }

        var assignment = this.scheduleAssignments[section.id];
        if(assignment.room_id) {
            $j.each(assignment.timeslots, function(index, timeslot) {
                var cell = this.matrix.getCell(assignment.room_id, timeslot);
                cell.select();
            }.bind(this));
        } else {
            section.directoryCell.select();
        }
        this.selectedSection = section;
        this.matrix.sectionInfoPanel.displaySection(section);
        this.availableTimeslots = this.getAvailableTimeslots(section);
        this.matrix.highlightTimeslots(this.availableTimeslots, section);


    };

    /**
     * Unselect the cells associated with the currently selected section, hide the section info
     * panel, and unhighlight the available cells to place the section.
     * @param override: What should the availability override status be?
     */
    this.unselectSection = function(override = false) {
        if(!this.selectedSection) {
            return;
        }
        var assignment = this.scheduleAssignments[this.selectedSection.id];
        if(assignment.room_id) {
            $j.each(assignment.timeslots, function(index, timeslot) {
                var cell = this.matrix.getCell(assignment.room_id, timeslot);
                cell.unselect();
            }.bind(this));
        } else {
            this.selectedSection.directoryCell.unselect();
        }

        this.selectedSection = null;
        this.matrix.sectionInfoPanel.hide();
        this.matrix.sectionInfoPanel.override = override;
        this.matrix.unhighlightTimeslots(this.availableTimeslots);

    };

    /**
     * Get the timeslots available for scheduling this section.
     * Returns an array of two lists.
     *
     * The first has all the timeslots where all teachers are available and
     * none are teaching.
     *
     * The second has all the timeslots where teachers are available but already teaching
     *
     * @param section: The section to check availability.
     */
    this.getAvailableTimeslots = function(section) {
        var availableTimeslots = [];
        var already_teaching = [];
        if(this.matrix.sectionInfoPanel.override){
            $j.each(this.matrix.timeslots.timeslots, function(index, timeslot) {
                availableTimeslots.push(timeslot.id);
            }.bind(this));
        } else {
            var availabilities = []
            $j.each(section.teacher_data, function(index, teacher) {
                var teacher_availabilities = teacher.availability.slice();
                teacher_availabilities = teacher_availabilities.filter(function(val) {
                    return this.matrix.timeslots.get_by_id(val);
                }.bind(this));
                $j.each(teacher.sections, function(index, section_id) {
                    var assignment = this.scheduleAssignments[section_id];
                    if(assignment && section_id != section.id) {
                        $j.each(assignment.timeslots, function(index, timeslot_id) {
                            var availability_index = teacher_availabilities.indexOf(timeslot_id);
                            if(availability_index >= 0) {
                                teacher_availabilities.splice(availability_index, 1);
                                already_teaching.push(timeslot_id);
                            }
                        }.bind(this));
                    }
                }.bind(this));
                availabilities.push(teacher_availabilities);
            }.bind(this));
            availableTimeslots = helpersIntersection(availabilities, true);
        }
        return [availableTimeslots, already_teaching];
    };

    /**
     * Get the teachers for a section as a list separated by a comma
     *
     * @param section: The section to get the teachers from.
     */
    this.getTeachersString = function(section) {
        var teacher_list = []
            $j.each(section.teacher_data, function(index, teacher) {
                teacher_list.push(teacher.first_name + " " + teacher.last_name);
            });
        var teachers = teacher_list.join(", ");
        return teachers;
    };

    this.getResourceString = function(section) {
        var resource_names = [];
        $j.each(section.resource_requests[section.id], function(index, resource_array) {
            resource_names.push("<li>" + resource_array[0].name + ": " + resource_array[1] + "</li>");
        });
        return "<ul>" + resource_names.join(" ") + "</ul>";

    };

    /**
     * Schedule a section of a class.
     *
     * @param section: The section to schedule
     * @param room_id: The name of the room to schedule it in
     * @param first_timeslot_id: The ID of the first timeslot to schedule the section in
     */
    this.scheduleSection = function(section, room_id, first_timeslot_id){
        var old_assignment = this.scheduleAssignments[section.id];
        var schedule_timeslots = this.matrix.timeslots.
            get_timeslots_to_schedule_section(section, first_timeslot_id);
        var override = this.matrix.sectionInfoPanel.override;

        // Make sure the assignment is valid
        if (!this.matrix.validateAssignment(section, room_id, schedule_timeslots).valid){
            return;
        }

        // Make sure section not locked
        if (section.schedulingLocked){
            this.matrix.messagePanel.addMessage("Error: the specified section is locked (" + section.schedulingComment + ")! Unlock it first.");
            this.unselectSection();
            return;
        }

        // Optimistically schedule the section locally before hearing back from the server
        this.scheduleSectionLocal(section, room_id, schedule_timeslots);
        this.apiClient.schedule_section(
            section.id,
            schedule_timeslots,
            room_id,
            override,
            function() {},
            // If there's an error, reschedule the section in its old location
            function(msg) {
                this.scheduleSectionLocal(section,
                    old_assignment.room_id,
                    old_assignment.timeslots);
                this.matrix.messagePanel.addMessage("Error: " + msg)
                console.log(msg);
            }.bind(this)
        );
        // Reset the availability override
        this.matrix.sectionInfoPanel.override = false;
    }


    /**
     * Make the local changes associated with scheduling a class and update the display
     *
     * @param section: The section to schedule
     * @param room_id: The name of the room to schedule it in
     * @param schedule_timeslots: The IDs of the timeslots to schedule the section in
     */
    this.scheduleSectionLocal = function(section, room_id, schedule_timeslots){
        var old_assignment = this.scheduleAssignments[section.id];

        // Check to see if we need to make any changes
        if(
            old_assignment.room_id == room_id &&
            JSON.stringify(old_assignment.timeslots)==JSON.stringify(schedule_timeslots)
            ){
            return;
        }

        // Unschedule from old place
        for (timeslot_index in old_assignment.timeslots) {
            var timeslot_id = old_assignment.timeslots[timeslot_index];
            var cell = this.matrix.getCell(old_assignment.room_id, timeslot_id);
            cell.removeSection();
        }
        if(this.selectedSection === section) {
            this.unselectSection();
        }


        // Add section to cells
        for(timeslot_index in schedule_timeslots){
            var timeslot_id = schedule_timeslots[timeslot_index];
            this.matrix.getCell(room_id, timeslot_id).addSection(section);
        }

        // Update the array that keeps track of the assignments
        this.scheduleAssignments[section.id] = {
            room_id: room_id,
            timeslots: schedule_timeslots,
            id: section.id
        };

        // Trigger the event that tells the directory to update itself.
        $j("body").trigger("schedule-changed");
    }

    /**
     * Make the selected section appear as a "ghost" on the schedule.
     *
     * @param room_id: The room that the class would go in
     * @param first_timeslot_id: The id of the first timeslot the class would go in
     */
    this.scheduleAsGhost = function(room_id, first_timeslot_id) {
        var schedule_timeslots = this.matrix.timeslots.
            get_timeslots_to_schedule_section(this.selectedSection, first_timeslot_id);
        $j.each(schedule_timeslots, function(index, timeslot_id) {
            this.matrix.getCell(room_id, timeslot_id).addGhostSection(this.selectedSection);
        }.bind(this));
        this.ghostScheduleAssignment = {'room_id': room_id, 'timeslots': schedule_timeslots};
    };

    /**
     * Remove the ghost section from the schedule.
     */
    this.unscheduleAsGhost = function() {
        $j.each(this.ghostScheduleAssignment.timeslots, function(index, timeslot_id) {
            this.matrix.getCell(this.ghostScheduleAssignment.room_id, timeslot_id).removeGhostSection();
        }.bind(this));
        this.ghostScheduleAssignment = {};
    };

    /**
     * Unschedule a section of a class.
     *
     * @param section: the section to unschedule
     */
    this.unscheduleSection = function(section){
        // Make sure section not locked
        if (section.schedulingLocked){
            this.matrix.messagePanel.addMessage("Error: the specified section is locked (" + section.schedulingComment + ")! Unlock it first.");
            this.unselectSection();
            return;
        }

        var old_assignment = this.scheduleAssignments[section.id];
        var old_room_id = old_assignment.room_id;
        var old_schedule_timeslots = old_assignment.timeslots;

        // Optimistically make local changes to unschedule the class
        this.unscheduleSectionLocal(section);
        this.apiClient.unschedule_section(
            section.id,
            function(){},
            // If the server returns an error, put the class back in its original spot
            function(msg){
                this.scheduleSectionLocal(section, old_room_id, old_schedule_timeslots);
                this.matrix.messagePanel.addMessage("Error: " + msg);
                console.log(msg);
            }.bind(this)
        );
    };

    /**
     * Set the comment and locked on a class.
     *
     * @param section: the section to update
     * @param comment: a string comment to post
     * @param locked: true if this class should be locked from scheduling
     * @param remote: true if this setComment request comes from the server and not local user
     */
    this.setComment = function(section, comment, locked, remote){
        if(section.schedulingComment == comment && section.schedulingLocked == locked) {
            return;
        }

        // go ahead and set section to new status
        // unlike other cases, we don't revert this update if the API call fails
        // this is because the comment/locked is a front-end helper
        //   if API call fails, user will still get message, and this way user
        //   can anyway continue scheduling this section
        section.schedulingComment = comment;
        section.schedulingLocked = locked;

        if(!remote) {
            this.apiClient.set_comment(section.id, comment, locked, function(){}, function(msg){
                this.matrix.messagePanel.addMessage("Error: " + msg);
                console.log(msg);
            }.bind(this));
            this.unselectSection();
        }

        // update cells in case we switched the locked flag
        var assignment = this.scheduleAssignments[section.id];
        if(assignment.room_id) {
            $j.each(assignment.timeslots, function(index, timeslot) {
                this.matrix.getCell(assignment.room_id, timeslot).update();
            }.bind(this));
        }
    }

    /**
     * Update the local interface to reflect unscheduling a class
     *
     * @param section: the section to unschedule
     */
    this.unscheduleSectionLocal = function(section) {
        this.scheduleSectionLocal(section, null, [])
    };


    this.getBaseUrlString = function() {
        var parser = document.createElement('a');
        parser.href = document.URL;
        return parser.pathname.slice(0, -("ajaxscheduling".length) - 1);
    };

}
