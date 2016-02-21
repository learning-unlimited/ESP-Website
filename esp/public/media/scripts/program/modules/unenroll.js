function setup() {
    // entry point
    setup_handlers.call(this);
    fetch_status.call(this);
    setInterval(poll_status.bind(this), 15000);
}

function fetch_status() {
    $j.getJSON(program_base_url + 'unenroll_status',
               handle_status.bind(this));
}

function poll_status() {
    $j.getJSON(program_base_url + 'unenroll_status?cache_only',
               handle_status.bind(this));
}

function handle_status(data) {
    // enrollments: { enrollment id -> (user id, section id) }
    // student_timeslots: { user id -> event id of first class timeslot }
    // section_timeslots: { section id -> event id of first timeslot }
    if (data !== null) {
        this.enrollments = data.enrollments;
        this.student_timeslots = data.student_timeslots;
        this.section_timeslots = data.section_timeslots;
        this.stale = false;
    }
    else {
        // cache_only returned none
        this.stale = true;
    }
    handle_update.call(this);
}

function handle_update(event) {
    // toggle timeslots before/after the current one
    if (event !== undefined) {
        update_checkboxes.call(this, event);
    }

    // recalculate data
    var students = selected_students.call(this);
    var sections = selected_sections.call(this);
    var enrollments = selected_enrollments.call(this, students, sections);

    // populate the form field to be submitted
    var submission = $j('#program_form').prop('selected_enrollments');
    submission.value = _.keys(enrollments);

    // enable the submit button if submissions is non-empty
    $j('#program_form [type=submit]').prop('disabled', _.isEmpty(enrollments));

    // display a message
    $j('#message').text("You have selected " + _.size(students) + " students to be dropped from " + _.size(sections) + " sections (" + _.size(enrollments) + " enrollments total)");

    // show "refresh data" link if data is non-stale
    $j('#refresh').toggle(this.stale);
}

function selected_enrollments(students, sections) {
    // set of students x set of sections -> set of enrollment ids
    return _.pick(this.enrollments, function (student_section) {
        var student = student_section[0];
        var section = student_section[1];
        return _.has(students, student) && _.has(sections, section);
    });
}

function selected_students() {
    // return the set of selected students, as an object
    // { user id -> value if student is selected }
    var timeslot_selected = selected_timeslots('student_timeslots');
    return _.pick(this.student_timeslots, function (ts) {
        return timeslot_selected[ts];
    });
}

function selected_sections() {
    // return the set of selected sections, as an object
    // { section id -> value if section is selected }
    var timeslot_selected = selected_timeslots('section_timeslots');
    return _.pick(this.section_timeslots, function (ts) {
        return timeslot_selected[ts];
    });
}

function selected_timeslots(name) {
    // return the set of selected timeslots, as an object
    // { timeslot id -> whether the timeslot is selected }
    // name is either "student_timeslots" or "section_timeslots"
    var elements = $j('#program_form').prop(name);
    return _.zipObject(_.map(elements, function (el) {
        return [el.value, el.checked];
    }));
}

function setup_handlers() {
    $j('#program_form').change(handle_update.bind(this));
    $j('#program_form').submit(function () {
        if (this.stale) {
            return confirm("The data on this page is out-of-date, and it is recommended to click Refresh Data before submitting. Are you sure you want to continue anyway?");
        }
    }.bind(this));
    $j('#refresh').click(fetch_status.bind(this));
}

function update_checkboxes(event) {
    // get all checkboxes in the same group
    var group = $j('#program_form').prop(event.target.name);
    var seq = parseInt(event.target.getAttribute('data-seq'), 10);
    _.each(group, function (other) {
        var other_seq = parseInt(other.getAttribute('data-seq'), 10);
        // if checked, check all earlier timeslots as well
        // if not checked, uncheck all later timeslots
        if (event.target.checked && other_seq <= seq ||
           !event.target.checked && other_seq >= seq) {
            other.checked = event.target.checked;
        }
    });
}

$j(document).ready(function () {
    setup.call({});
});
