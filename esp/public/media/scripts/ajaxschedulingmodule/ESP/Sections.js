/**
 * Stores the section data and the UI state including the selected section, filter, and search term.
 * Provides helper methods for accessing and scheduling sections.
 * Has a pointer to the Matrix when bindMatrix is called.
 *
 * @params sections_data: The raw section data
 * @params section_details_data: The AJAX section detail data
 * @params teacher_data: The raw teacher data for populating the sections
 * @params scheduleAssignments: The schedule assignments
 * @params apiClient: The object that can communicate with the server
 */
function Sections(sections_data, section_details_data, categories_data, teacher_data, moderator_data, scheduleAssignments, apiClient) {
    this.sections_data = sections_data;
    this.categories_data = categories_data;
    this.teacher_data = teacher_data;
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

    // Set up sort
    this.sortObject = {field: "id", type: "asc"}
    $j("#class-sort-field, [name='class-sort-type']").on("change", function(evt) {
        if(evt.currentTarget.id === "class-sort-field") {
            this.sortObject.field = evt.currentTarget.value;
        } else {
            this.sortObject.type = evt.currentTarget.value;
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

            section.moderator_data = []
            $j.each(section.moderators, function(index, moderator_id) {
                section.moderator_data.push(moderator_data[moderator_id]);
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
            if (section.status < 0) {
                // filter out rejected and cancelled sections
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
        // sort sections based on selected field
        switch(this.sortObject.field) {
            case "id":
                returned_sections.sort((a, b) => a.id - b.id);
                break;
            case "category":
                returned_sections.sort((a, b) => a.category.localeCompare(b.category));
                break;
            case "length":
                returned_sections.sort((a, b) => a.length - b.length);
                break;
            case "capacity":
                returned_sections.sort((a, b) => a.class_size_max - b.class_size_max);
                break;
            case "availability":
                returned_sections.sort((a, b) => this.getAvailableTimeslots(a)[0].length - this.getAvailableTimeslots(b)[0].length);
                break;
            case "hosedness": // proportion of total availability that teachers are already teaching
               returned_sections.sort(function(a, b) {
                   var a_times = this.getAvailableTimeslots(a);
                   var b_times = this.getAvailableTimeslots(b);
                   return a_times[1].length/(a_times[0].length + a_times[1].length) - b_times[1].length/(b_times[0].length + b_times[1].length);
               }.bind(this));
               break;
        }
        // reverse if descending selected
        if(this.sortObject.type === "des") returned_sections.reverse()
        return returned_sections;
        
    };

    /**
     * Select the cells associated with this section, put it on the section info
     * panel, and highlight the available cells to place the section.
     *
     * @param section: The section to select
     */
    this.selectSection = function(section) {
        if(has_moderator_module === "True" && this.matrix.moderatorDirectory.selectedModerator) {
            this.matrix.moderatorDirectory.unselectModerator();
        }
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
        this.unscheduleAsGhost();
    };

    /**
     * Get the timeslots available for scheduling this section.
     * Returns an array of two lists.
     *
     * The first has all the timeslots where all teachers/moderators are available and
     * none are teaching or moderating.
     *
     * The second has all the timeslots where teachers/moderators are available but
     * already teaching or moderating
     *
     * @param section: The section to check availability.
     * @param ignore_sections: An optional array of sections to ignore.
     */
    this.getAvailableTimeslots = function(section, ignore_sections=[]) {
        var availableTimeslots = [];
        var already_teaching_or_moderating = [];
        if(this.matrix.sectionInfoPanel.override){
            $j.each(this.matrix.timeslots.timeslots, function(index, timeslot) {
                availableTimeslots.push(timeslot.id);
            }.bind(this));
        } else {
            var availabilities = []
            // Get teacher availabilities
            $j.each(section.teacher_data, function(index, teacher) {
                var teacher_availabilities = teacher.availability.slice();
                teacher_availabilities = teacher_availabilities.filter(function(val) {
                    return this.matrix.timeslots.get_by_id(val);
                }.bind(this));
                $j.each(teacher.sections, function(index, section_id) {
                    var assignment = this.scheduleAssignments[section_id];
                    if(assignment && section_id != section.id && !ignore_sections.includes(this.getById(section_id))) {
                        $j.each(assignment.timeslots, function(index, timeslot_id) {
                            var availability_index = teacher_availabilities.indexOf(timeslot_id);
                            if(availability_index >= 0) {
                                teacher_availabilities.splice(availability_index, 1);
                                already_teaching_or_moderating.push(timeslot_id);
                            }
                        }.bind(this));
                    }
                }.bind(this));
                // In case a teacher of this section is also a moderator of other sections
                if(teacher.id in moderator_data) {
                    $j.each(moderator_data[teacher.id].sections, function(index, section_id) {
                        var assignment = this.scheduleAssignments[section_id];
                        if(assignment && section_id != section.id && !ignore_sections.includes(this.getById(section_id))) {
                            $j.each(assignment.timeslots, function(index, timeslot_id) {
                                var availability_index = teacher_availabilities.indexOf(timeslot_id);
                                if(availability_index >= 0) {
                                    teacher_availabilities.splice(availability_index, 1);
                                    already_teaching_or_moderating.push(timeslot_id);
                                }
                            }.bind(this));
                        }
                    }.bind(this));
                }
                availabilities.push(teacher_availabilities);
            }.bind(this));
            // Get moderator availabilities
            $j.each(section.moderator_data, function(index, moderator) {
                var moderator_availabilities = moderator.availability.slice();
                moderator_availabilities = moderator_availabilities.filter(function(val) {
                    return this.matrix.timeslots.get_by_id(val);
                }.bind(this));
                $j.each(moderator.sections, function(index, section_id) {
                    var assignment = this.scheduleAssignments[section_id];
                    if(assignment && section_id != section.id && !ignore_sections.includes(this.getById(section_id))) {
                        $j.each(assignment.timeslots, function(index, timeslot_id) {
                            var availability_index = moderator_availabilities.indexOf(timeslot_id);
                            if(availability_index >= 0) {
                                moderator_availabilities.splice(availability_index, 1);
                                already_teaching_or_moderating.push(timeslot_id);
                            }
                        }.bind(this));
                    }
                }.bind(this));
                // In case a teacher of this section is also a moderator of other sections
                if(moderator.id in teacher_data) {
                    $j.each(teacher_data[moderator.id].sections, function(index, section_id) {
                        var assignment = this.scheduleAssignments[section_id];
                        if(assignment && section_id != section.id && !ignore_sections.includes(this.getById(section_id))) {
                            $j.each(assignment.timeslots, function(index, timeslot_id) {
                                var availability_index = moderator_availabilities.indexOf(timeslot_id);
                                if(availability_index >= 0) {
                                    moderator_availabilities.splice(availability_index, 1);
                                    already_teaching_or_moderating.push(timeslot_id);
                                }
                            }.bind(this));
                        }
                    }.bind(this));
                }
                availabilities.push(moderator_availabilities);
            }.bind(this));
            availableTimeslots = _.intersection(...availabilities); // From the lodash library
        }
        return [availableTimeslots, already_teaching_or_moderating];
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

    this.getModeratorsString = function(section) {
        var moderator_list = []
            $j.each(section.moderator_data, function(index, moderator) {
                moderator_list.push(moderator.first_name + " " + moderator.last_name);
            });
        var moderators = moderator_list.join(", ");
        return moderators;
    };

    /**
     * Schedule a section of a class.
     *
     * @param section: The section to schedule
     * @param room_id: The name of the room to schedule it in
     * @param first_timeslot_id: The ID of the first timeslot to schedule the section in
     * @param callback: A function to run upon success
     */
    this.scheduleSection = function(section, room_id, first_timeslot_id, callback = function() {}){
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
            this.matrix.messagePanel.addMessage("Error: the specified section is locked (" + section.schedulingComment + ")! Unlock it first.", color = "red");
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
            callback,
            // If there's an error, reschedule the section in its old location
            function(msg) {
                this.scheduleSectionLocal(section,
                    old_assignment.room_id,
                    old_assignment.timeslots);
                this.matrix.messagePanel.addMessage("Error: " + msg, color = "red")
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

        // Update cell coloring
        this.matrix.updateCells();
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
        this.ghostScheduleAssignment = {'room_id': room_id, 'timeslots': schedule_timeslots};
        $j.each(schedule_timeslots, function(index, timeslot_id) {
            this.matrix.getCell(room_id, timeslot_id).addGhostSection(this.selectedSection);
        }.bind(this));
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
    this.unscheduleSection = function(section, callback = function(){}){
        // Make sure section not locked
        if (section.schedulingLocked){
            this.matrix.messagePanel.addMessage("Error: the specified section is locked (" + section.schedulingComment + ")! Unlock it first.", color = "red");
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
            callback,
            // If the server returns an error, put the class back in its original spot
            function(msg){
                this.scheduleSectionLocal(section, old_room_id, old_schedule_timeslots);
                this.matrix.messagePanel.addMessage("Error: " + msg, color = "red");
                console.log(msg);
            }.bind(this)
        );
    };

    /**
     * Update the local interface to reflect unscheduling a class
     *
     * @param section: the section to unschedule
     */
    this.unscheduleSectionLocal = function(section) {
        this.scheduleSectionLocal(section, null, [])
    };

    this.swapSections = function(section1, section2) {
        // Abort if either section is locked
        if (section1.schedulingLocked){
            this.matrix.messagePanel.addMessage("Error: the first selected section is locked (" + section1.schedulingComment + ")! Unlock it first.", color = "red");
            this.unselectSection();
            return;
        } else if (section2.schedulingLocked){
            this.matrix.messagePanel.addMessage("Error: the second selected section is locked (" + section2.schedulingComment + ")! Unlock it first.", color = "red");
            this.unselectSection();
            return;
        }

        // Get the current assignments for the sections
        var old_assignment1 = this.scheduleAssignments[section1.id];
        var old_assignment2 = this.scheduleAssignments[section2.id];
        // Extract room and timeslots from assignments
        var room1 = old_assignment1.room_id;
        var room2 = old_assignment2.room_id;
        var old_timeslots1 = old_assignment1.timeslots;
        var old_timeslots2 = old_assignment2.timeslots;

        if (room1 === null && room2 === null) {
            return;
        }
        if (room1 === null){
            // If section 1 is unscheduled, section 2 will become unscheduled
            // Repeat section 1 for each timeslot it needs
            var temp_timeslots = this.matrix.timeslots.get_timeslots_to_schedule_section(section1, old_timeslots2[0]);
            var swapping_sections1 = Array(temp_timeslots.length).fill(section1);
        } else {
            // Get timeslots to schedule section 2 in classroom 1
            var new_timeslots2 = this.matrix.timeslots.get_timeslots_to_schedule_section(section2, old_timeslots1[0]);

            // Abort if there isn't enough time for section 2 in classroom 1
            if(new_timeslots2 === null){
                this.matrix.messagePanel.addMessage("Error: not enough time to swap the second section to the new room.", color = "red");
                this.unselectSection();
                return;
            }

            // Get the sections you'll be swapping with
            var swapping_sections1 = new_timeslots2.map(ts => this.matrix.getCell(room1, ts).section);
        }
        if (room2 === null){
            // If section 2 is unscheduled, section 1 will become unscheduled
            // Repeat section 2 for each timeslot it needs
            var temp_timeslots = this.matrix.timeslots.get_timeslots_to_schedule_section(section2, old_timeslots1[0]);
            var swapping_sections2 = Array(temp_timeslots.length).fill(section2);
        } else {
            // Get timeslots to schedule section 1 in classroom 2
            var new_timeslots1 = this.matrix.timeslots.get_timeslots_to_schedule_section(section1, old_timeslots2[0]);

            // Abort if there isn't enough time for section 1 in classroom 2
            if(new_timeslots1 === null){
                this.matrix.messagePanel.addMessage("Error: not enough time to swap the first section to the new room.", color = "red");
                this.unselectSection();
                return;
            }

            // Get the sections you'll be swapping with
            var swapping_sections2 = new_timeslots1.map(ts => this.matrix.getCell(room2, ts).section);
        }

        // If there's more than one swapping section, confirm the user is OK with this
        if(_.uniq(swapping_sections1.filter(Boolean)).length > 1 && !confirm("More than one section will need to be swapped from the old room. Is this OK?")){
            return;
        } else if(_.uniq(swapping_sections2.filter(Boolean)).length > 1 && !confirm("More than one section will need to be swapped from the new room. Is this OK?")){
            return;
        }
        $j(".ui-tooltip").hide() // There seems to be a bug or something caused by the confirm box that causes the tooltip to get stuck
        var old_assignments1 = _.uniq(swapping_sections1.filter(Boolean)).map(sec => ({"section": sec.id, "timeslots": this.scheduleAssignments[sec.id].timeslots, "room_id": room1}));
        var old_assignments2 = _.uniq(swapping_sections2.filter(Boolean)).map(sec => ({"section": sec.id, "timeslots": this.scheduleAssignments[sec.id].timeslots, "room_id": room2}));
        var ignore_sections = _.uniq(_.union(swapping_sections1, swapping_sections2));

        // Determine new schedule for room 1 sections and validate assignments
        var new_assignments1 = [];
        var start_slot = this.matrix.timeslots.get_by_id(old_timeslots2[0]);
        for(var sec of swapping_sections1){
            if(room2 === null) {
                if(sec){
                    new_assignments1.push({"section": sec.id, "timeslots": [], "room_id": room2});
                }
            } else {
                if(sec){
                    if(new_assignments1.length == 0 || sec.id !== new_assignments1[new_assignments1.length - 1].section){
                        var new_timeslots = this.matrix.timeslots.get_timeslots_to_schedule_section(sec, start_slot.id);
                        var valid = this.matrix.validateAssignment(sec, room2, new_timeslots, ignore_sections);
                        if(!valid.valid){
                            console.log(valid.reason);
                            this.matrix.messagePanel.addMessage(valid.reason, color = "red");
                            this.unselectSection();
                            return;
                        }
                        new_assignments1.push({"section": sec.id, "timeslots": new_timeslots, "room_id": room2});
                        start_slot = this.matrix.timeslots.get_by_order(this.matrix.timeslots.get_by_id(new_timeslots[new_timeslots.length - 1]).order + 1);
                    }
                } else {
                    start_slot = this.matrix.timeslots.get_by_order(start_slot.order + 1);
                }
            }
        }

        // Determine new schedule for room 2 sections and validate assignments
        var new_assignments2 = [];
        var start_slot = this.matrix.timeslots.get_by_id(old_timeslots1[0])
        for(var sec of swapping_sections2){
            if(room1 === null) {
                if(sec){
                    new_assignments2.push({"section": sec.id, "timeslots": [], "room_id": room1});
                }
            } else {
                if(sec){
                    if(new_assignments2.length == 0 || sec.id !== new_assignments2[new_assignments2.length - 1].section){
                        var new_timeslots = this.matrix.timeslots.get_timeslots_to_schedule_section(sec, start_slot.id);
                        var valid = this.matrix.validateAssignment(sec, room1, new_timeslots, ignore_sections);
                        if(!valid.valid){
                            console.log(valid.reason);
                            this.matrix.messagePanel.addMessage(valid.reason, color = "red");
                            this.unselectSection();
                            return;
                        }
                        new_assignments2.push({"section": sec.id, "timeslots": new_timeslots, "room_id": room1});
                        start_slot = this.matrix.timeslots.get_by_order(this.matrix.timeslots.get_by_id(new_timeslots[new_timeslots.length - 1]).order + 1);
                    }
                } else {
                    start_slot = this.matrix.timeslots.get_by_order(start_slot.order + 1);
                }
            }
        }

        var override = this.matrix.sectionInfoPanel.override;
        // Make local changes (asynchronously)
        this.swapSectionsLocal(new_assignments1, new_assignments2);
        
        // Make server changes
        this.apiClient.swap_sections(
            new_assignments1,
            new_assignments2,
            override,
            function() {
                this.matrix.scheduler.changelogFetcher.getChanges();
            }.bind(this),
            // If there's an error, locally reschedule the sections in their old locations
            function(msg) {
                this.swapSectionsLocal(old_assignments1, old_assignments2);
                this.matrix.messagePanel.addMessage("Error: " + msg, color = "red");
                console.log(msg);
            }.bind(this)
        );

        // Reset the availability override
        this.matrix.sectionInfoPanel.override = false;
    };

    /**
     * Make the local changes associated with swapping sections and update the display
     *
     * @param assignments1: The new assignments for the section(s) in room 1
     * @param assignments2: The new assignments for the section(s) in room 2
     */
    this.swapSectionsLocal = function(assignments1, assignments2){
        // Unschedule the section(s) in room 1
        for(var asmt of assignments1){
            this.unscheduleSectionLocal(this.getById(asmt.section));
        }
        // Schedule the section(s) from room 2 into room 1
        for(var asmt of assignments2){
            if(asmt.room_id !== null){
                this.scheduleSectionLocal(this.getById(asmt.section), asmt.room_id, asmt.timeslots);
            } else {
                this.unscheduleSectionLocal(this.getById(asmt.section));
            }
        }
        // Schedule the section(s) from room 1 into room 2
        for(var asmt of assignments1){
            if(asmt.room_id !== null){
                this.scheduleSectionLocal(this.getById(asmt.section), asmt.room_id, asmt.timeslots);
            } else {
                this.unscheduleSectionLocal(this.getById(asmt.section));
            }
        }
    }

    /**
     * Set the comment and locked on a class.
     *
     * @param section: the section to update
     * @param comment: a string comment to post
     * @param locked: true if this class should be locked from scheduling
     * @param remote: true if this setComment request comes from the server and not local user
     */
    this.setComment = function(section, comment, locked, remote){
        updateCells = function() {
            var assignment = this.scheduleAssignments[section.id];
            if(assignment.room_id) {
                $j.each(assignment.timeslots, function(index, timeslot) {
                    this.matrix.getCell(assignment.room_id, timeslot).update();
                }.bind(this));
            }
        }.bind(this);

        if(section.schedulingComment == comment && section.schedulingLocked == locked) {
            return;
        }

        var old_comment = section.schedulingComment;
        var old_locked = section.schedulingLocked;

        section.schedulingComment = comment;
        section.schedulingLocked = locked;

        if(!remote) {
            this.apiClient.set_comment(section.id, comment, locked, function(){
                // if successful, update the appearance of the cells
                updateCells();
                this.unselectSection();
            }.bind(this), function(msg){
                // if unsuccessful, revert the comment locked status and show an error
                section.schedulingComment = old_comment;
                section.schedulingLocked = old_locked;
                this.matrix.messagePanel.addMessage("Error: " + msg, color = "red");
                console.log(msg);
                this.unselectSection();
            }.bind(this));
        } else {
            // if this is from the changelog, just update the appearance of the cells
            updateCells();
            this.unselectSection();
        }
    }


    this.getBaseUrlString = function() {
        var parser = document.createElement('a');
        parser.href = document.URL;
        return parser.pathname.slice(0, -("ajaxscheduling".length) - 1);
    };

}
