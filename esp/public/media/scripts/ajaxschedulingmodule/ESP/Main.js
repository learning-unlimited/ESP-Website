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

// Set the width and height of the matrix and directory
var resizeElements = function() {
        var window_height = window.innerHeight - 20;
        var window_width = window.innerWidth - 20;
        $j("#side-panel-wrapper").height(window_height)
        .width(window_width/4);
        $j("#matrix-div").height(window_height)
        .width(window_width*3/4);
};

// Resize window handler
window.onresize = resizeElements;

// Fetch the data from the server
var data = {};
json_get('lunch_timeslots', {}, function(lunch_timeslots) {
    json_fetch(['sections_admin', 'lunch_timeslots', 'timeslots', 'rooms', 'schedule_assignments', "resource_types"], function(){
        console.log(data)
        resizeElements();
                
        $j("div#side-panel").tabs();
        // Create a new Scheduler which does the rest
        var s = new Scheduler(
            data,
            $j("#directory"),
            $j("#matrix-div"),
            $j("#message-div"),
            $j("#section-info-div"),
            last_applied_index,
            5000
            );
        s.render();
    }, data);
    data['lunch_timeslots'] = Object.keys(lunch_timeslots['timeslots']);
    }, function() {});
