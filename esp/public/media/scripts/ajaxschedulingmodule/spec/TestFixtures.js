function teacher_fixture() {
    return {
        1: {
            first_name: "Alyssa P.",
            last_name: "Hacker",
            availability: [1],
            sections: 3329, 
        },
        2: {
            first_name: "Ben",
            last_name: "Bitdiddle",
            availability: [1, 2],
            sections: 3538,
        },
    };
};

function time_fixture() {
    return {
	1: {
	    label:  "first timeslot",
	    start:  [2010, 4, 17, 10, 0, 0],
	    end:  [2010, 4, 17, 10, 50, 0],
	    id: 1
	},
	2: {
	    label:  "second timeslot",
	    start:  [2010, 4, 17, 11, 0, 0],
	    end:  [2010, 4, 17, 11, 50, 0],
	    id: 2
	}
    };
};

function time_fixture_with_order(){
    return {
	1: {
	    label:  "first timeslot",
	    start:  [2010, 4, 17, 10, 0, 0],
	    end:  [2010, 4, 17, 10, 50, 0],
	    order: 0,
	    id: 1
	},
	2: {
	    label:  "second timeslot",
	    start:  [2010, 4, 17, 11, 0, 0],
	    end:  [2010, 4, 17, 11, 50, 0],
	    order: 1,
	    id: 2
	}
    };
};

function time_fixture_out_of_order() {
    return {
	2: {
	    label:  "first timeslot",
	    start:  [2010, 4, 17, 10, 0, 0],
	    end:  [2010, 4, 17, 10, 50, 0],
	    id: 2
	},
	1: {
	    label:  "second timeslot",
	    start:  [2010, 4, 17, 11, 0, 0],
	    end:  [2010, 4, 17, 11, 50, 0],
	    id: 1
	}
    };
};

function room_fixture() {
    return {
	"room-1": {
	    availability: [1, 2],
        num_students: 23,
        id: "room-1"
	},
	"room-2": {
	    availability: [1, 2],
        num_students: 7,
        id: "room-2"
	}
    };
};

function schedule_assignments_fixture() {
    return {
	3329: {
	    room_name: "room-1",
	    id: 3329,
	    timeslots: [1, 2]
	},
	3538: {
	    room_name: null,
	    id: 3538,
	    timeslots: []
	}
    };
};

function empty_schedule_assignments_fixture() {
    return {
	3329: {
	    id: 3329,
	    timeslots: []
	},
	3538: {
	    id: 3538,
	    timeslots: []
	}
    };
};

function section_1() {
    return {
	    status: 10, 
	    category: 'S', 
	    parent_class: 3188, 
	    emailcode: 'S3188s1', 
	    index: 1, 
	    title: "Fascinating Science Phenomena", 
	    category_id: 17, 
	    class_size_max: 150, 
	    length: 1, 
	    grade_min: 7, 
	    num_students: 42, 
	    grade_max: 12, 
	    id: 3329, 
	    teachers: [1, 2]
	};
};

function section_2() {
    return {
	    status: 10, 
	    category: 'M', 
	    parent_class: 3343, 
	    emailcode: 'M3343s1', 
	    index: 1, 
	    title: "Become a LaTeX Guru", 
	    category_id: 16, 
	    class_size_max: 15, 
	    length: 1.83, 
	    grade_min: 7, 
	    num_students: 14, 
	    grade_max: 12, 
	    id: 3538, 
	    teachers: [2]
	};
};

function sections_fixture() {
    return {
	3329: section_1(), 
	3538: section_2()
    };
};

function matrix_fixture() {
    var modified_room_fixture = room_fixture()
	modified_room_fixture["room-2"].availability = [2]
	return new Matrix(time_fixture(), modified_room_fixture,
                      room_fixture(), schedule_assignments_fixture(),
		              sections_fixture(), $j("<div/>"), $j("<div/>"),
		              new FakeApiClient());
};
