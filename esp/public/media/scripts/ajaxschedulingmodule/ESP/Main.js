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
    $j("#directory-wrapper-div").height(window_height);
    $j("#matrix-div").height(window_height);

    var s = new Scheduler(
	data,
	$j("#directory-div"),
	$j("#matrix-div"),
	$j("#garbage-div"),
	last_applied_index,
	5000
    );
    s.render();
}, 
data);
