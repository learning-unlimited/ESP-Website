/**
 * The entry point for the scheduler
 */

// Set the width and height of the matrix and directory
var resizeElements = function() {
    var window_height = window.innerHeight - 20;
    var window_width = window.innerWidth - 20;
    $j("#matrix-div").height(window_height)
        .width(window_width*3/4);
    $j("#side-panel-wrapper").width(window_width/4).height(window_height);
};

// Resize window handler
window.onresize = resizeElements;

// Fetch the data from the server
var data = {};
json_get('lunch_timeslots', {}, function(lunch_timeslots) {
    $j.getJSON('ajax_section_details', function(section_details) {
        json_fetch(['sections_admin', 'lunch_timeslots', 'timeslots', 'rooms', 'schedule_assignments', 'resource_types', 'categories', 'moderators'], function(){
            console.log(data)
            resizeElements();

            $j("div#side-panel").tabs();
            // Create a new Scheduler which does the rest
            var s = new Scheduler(
                data,
                $j("#directory"),
                $j("#moderator-directory"),
                $j("#matrix-div"),
                $j("#message-div"),
                $j("#section-info-div"),
                $j("#commentDialog"),
                5000
            );
            s.render();
        }, data);
        data['section_details'] = section_details;
    });
    data['lunch_timeslots'] = Object.keys(lunch_timeslots['timeslots']);
}, function() {});
