function time_fixture() {
    return {
	1: {
	    label:  "first timeslot"
	},
	2: {
	    label:  "second timeslot"
	}
    }
}

function room_fixture() {
    return {
	"room-1": {},
	"room-2": {}
    }
}

//TODO:  like this??
function schedule_assignments_fixture() {
    return {
	3329: {
	    room_name: "room-1",
	    id: 3329,
	    timeslots: [1, 2]
	},
	3538: {
	    id: 3538,
	    timeslots: []
	}
    }
}

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
    }
}

//TODO:  we don't need all this data.  Can we pare it down?
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
	    length: 1.83, 
	    grade_min: 7, 
	    num_students: 42, 
	    grade_max: 12, 
	    id: 3329, 
	    teachers: [6460]
	}
}

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
	    teachers: [45225]
	}
}

function sections_fixture() {
    return {
	3329: section_1(), 
	3538: section_2()
    }
}
