/**
 * The entry point for the scheduler
 */
// For the changelog
var last_applied_index = 0;
$j.getJSON('ajax_schedule_last_changed', function(data, status) {
    if (status == "success") {
        last_applied_index = data['latest_index'];
    }
});

// Fetch the data from the server
var data = {};
json_fetch(['sections', 'timeslots', 'rooms', 'schedule_assignments'], function(){
    console.log(data)

    // Set the width and height of the matrix and directory
    var window_height = window.innerHeight - 20;
    var window_width = window.innerWidth - 20;
    $j("#directory-wrapper-div").height(window_height)
        .width(window_width/4);
    $j("#matrix-div").height(window_height)
        .width(window_width*3/4);

    // Create a new Scheduler which does the rest
    var s = new Scheduler(
	    data,
	    $j("#directory-div"),
	    $j("#matrix-div"),
        $j("#message-div"),
        $j("#section-info-div"),
	    last_applied_index,
	    5000
    );
    s.render();
}, 
data);
