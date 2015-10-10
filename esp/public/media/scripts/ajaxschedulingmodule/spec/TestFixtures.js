/**
 * Here's the fake schedule:
 *
 * Legend:
 *  xxxxx: disabled cell
 *  top row: timeslot ids (num_students)
 *  left column: room ids
 *  ||: boundary between days
 *  numbers in cells: IDs of sections
 *
 *             |  3  |  5  ||  7  |  11  |  13  |
 * ----------------------------------------------
 * room-1 (30) |S11s1|     ||     |xxxxxx|xxxxxx|
 * ----------------------------------------------
 * room-2 (10) |     |     ||xxxxx|     A22     |
 * ----------------------------------------------
 * room-3 (100)|     |xxxxx||xxxxx|      |      |
 * ----------------------------------------------
 *
 * Classes:
 * --------------------
 *   code    length   availability       teachers
 * - S11s1   1        3, 5               1, 2
 * - S11s2   1        3, 5               1, 2
 * - A22s1   2        11, 13             4
 * - S33s1   2        3, 5, 7, 11        1
 * - A44s1   1        7, 11, 13          3
 * - M55S1   1        7, 11              1, 3
 */

function teacher_fixture() {
    return {
        1: {
            id: 1,
            first_name: "Alyssa P.",
            last_name: "Hacker",
            username: "aphacker",
            availability: [3, 5, 7, 11],
            sections: [1, 2, 4, 6],
        },
        2: {
            id: 2,
            first_name: "Ben",
            last_name: "Bitdiddle",
            username: "bitdiddle",
            availability: [3, 5],
            sections: [1, 2],
        },
        3: {
            id: 3,
            first_name: "Edward S",
            last_name: "Pembroke",
            username: "esp",
            availability: [7, 11, 13],
            sections: [5, 6],
        },
        4: {
            id: 4,
            first_name: "Tim",
            last_name: "Beaver",
            username: "tbeaver",
            availability: [11, 13],
            sections: [3],
        },
    };
};

function time_fixture() {
    return {
        7: {
            label:  "third timeslot",
            short_description: "slot 1",
            start:  [2010, 4, 18, 10, 5, 0],
            end:  [2010, 4, 18, 10, 55, 0],
            id: 7,
            order: 3,
        },
        5: {
            label:  "second timeslot",
            short_description: "slot 2",
            start:  [2010, 4, 17, 11, 5, 0],
            end:  [2010, 4, 17, 11, 55, 0],
            id: 5,
            order: 2,
        },
        3: {
            label:  "first timeslot",
            short_description: "slot 1",
            start:  [2010, 4, 17, 10, 5, 0],
            end:  [2010, 4, 17, 10, 55, 0],
            id: 3,
            order: 1,
        },
        11: {
            label:  "fourth timeslot",
            short_description: "slot 4",
            start:  [2010, 4, 18, 11, 5, 0],
            end:  [2010, 4, 18, 11, 55, 0],
            id: 11,
            order: 4,
        },
        13: {
            label:  "fifth timeslot",
            short_description: "slot 5",
            start:  [2010, 4, 18, 12, 5, 0],
            end:  [2010, 4, 18, 12, 55, 0],
            id: 13,
            order: 5,
        },
    };
};

function room_fixture() {
    return {
        "room-1": {
            availability: [3, 5, 7],
            num_students: 23,
            id: "room-1",
            text: "room-1",
            uid: "room-1",
        },
        "room-2": {
            availability: [3, 5, 11, 13],
            num_students: 7,
            id: "room-2",
            text: "room-2",
            uid: "room-2",
        },
        "room-3": {
            availability: [3, 11, 13],
            num_students: 7,
            id: "room-3",
            text: "room-3",
            uid: "room-3",
        },
    };
};

function section_1() {
    return {
        status: 10,
        category: 'S',
        parent_class: 11,
        emailcode: 'S11s1',
        index: 1,
        title: "Fascinating Science Phenomena",
        category_id: 1,
        class_size_max: 150,
        length: .83,
        grade_min: 9,
        num_students: 0,
        grade_max: 12,
        id: 1,
        teachers: [1, 2],
        resource_requests: {1: []}
    };
};

function section_1b() {
    return {
        status: 10,
        category: 'S',
        parent_class: 11,
        emailcode: 'S11s2',
        index: 1,
        title: "Fascinating Science Phenomena",
        category_id: 1,
        class_size_max: 150,
        length: .83,
        grade_min: 9,
        num_students: 0,
        grade_max: 12,
        id: 2,
        teachers: [1, 2],
        resource_requests: {2: []}
    };
};

function section_2() {
    return {
        status: 10,
        category: 'A',
        parent_class: 22,
        emailcode: 'A22s1',
        index: 2,
        title: "Art History",
        category_id: 2,
        class_size_max: 75,
        length: 1.83,
        grade_min: 10,
        num_students: 0,
        grade_max: 11,
        id: 3,
        teachers: [4],
        resource_requests: {3: []}
    };
};

function section_3() {
    return {
        status: 10,
        category: 'S',
        parent_class: 33,
        emailcode: 'S33s1',
        index: 4,
        title: "Hands on Science",
        category_id: 1,
        class_size_max: 3,
        length: 1.83,
        grade_min: 9,
        num_students: 0,
        grade_max: 10,
        id: 4,
        teachers: [1],
        resource_requests: {4: []}
    };
};

function section_4() {
    return {
        status: 10,
        category: 'A',
        parent_class: 44,
        emailcode: 'A44s1',
        index: 5,
        title: "Drawing 101",
        category_id: 2,
        class_size_max: 50,
        length: 1.83,
        grade_min: 9,
        num_students: 0,
        grade_max: 12,
        id: 5,
        teachers: [3],
        resource_requests: {5: []}
    };
};

function section_5() {
    return {
        status: 10,
        category: 'M',
        parent_class: 55,
        emailcode: 'M55s1',
        index: 6,
        title: "Representation Theory",
        category_id: 3,
        class_size_max: 25,
        length: 1.83,
        grade_min: 10,
        num_students: 0,
        grade_max: 12,
        id: 6,
        teachers: [1, 3],
        resource_requests: {6: []}
    };
};

function section_fixture() {
    return {
        1: section_1(),
        2: section_1b(),
        3: section_2(),
        4: section_3(),
        5: section_4(),
        6: section_5(),
    };
};


function schedule_assignment_fixture() {
    return {
        1: {
            room_name: "room-1",
            id: 1,
            timeslots: [3]
        },
        2: {
            room_name: null,
            id: 2,
            timeslots: []
        },
        3: {
            room_name: "room-2",
            id: 3,
            timeslots: [11, 13]
        },
        4: {
            room_name: null,
            id: 4,
            timeslots: []
        },
        5: {
            room_name: null,
            id: 5,
            timeslots: []
        },
        6: {
            room_name: null,
            id: 6,
            timeslots: []
        }
    };
};
