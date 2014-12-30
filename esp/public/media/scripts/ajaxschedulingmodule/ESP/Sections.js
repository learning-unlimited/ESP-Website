function Sections(sections_data, teacher_data, scheduleAssignments) {
    this.scheduleAssignments = scheduleAssignments;
    this.init = function() {
        $j.each(sections_data, function(section_id, section) {
            section.teacher_data = []
            $j.each(section.teachers, function(index, teacher_id) {
                section.teacher_data.push(teacher_data[teacher_id]);
            });
        });
    };

    this.init();

    this.getById = function(section_id) {
        return sections_data[section_id];
    };

    this.getAvailableTimeslots = function(section) {
        var availabilities = [];
        var already_teaching = [];        
        $j.each(section.teacher_data, function(index, teacher) {
            var teacher_availabilities = teacher.availability.slice();
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
        var availableTimeslots = helpersIntersection(availabilities, true);
        return [availableTimeslots, already_teaching];
    };

    this.getTeachersString = function(section) {
        var teacher_list = []
        $j.each(section.teacher_data, function(index, teacher) {
            teacher_list.push(teacher.first_name + " " + teacher.last_name);
        });
        var teachers = teacher_list.join(", ");
        return teachers;
    };


}
