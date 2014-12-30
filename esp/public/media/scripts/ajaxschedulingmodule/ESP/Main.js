var last_applied_index = 0;
var data = {}
$j.getJSON('ajax_schedule_last_changed', function(data, status) {
    if (status == "success") {
        last_applied_index = data['latest_index'];
    }
});

data = {};
json_fetch(['sections', 'timeslots', 'rooms', 'schedule_assignments'], function(){
    console.log(data)

    var window_height = window.innerHeight - 20;
    var window_width = window.innerWidth - 20;
    $j("#directory-wrapper-div").height(window_height)
        .width(window_width/4);
    $j("#matrix-div").height(window_height)
        .width(window_width*3/4);




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
