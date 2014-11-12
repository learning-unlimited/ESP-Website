var data = {};

json_fetch(['sections', 'timeslots', 'rooms', 'schedule_assignments'], function(){
    var window_height = window.innerHeight - 20;
    $j("#directory-wrapper-div").height(window_height);
    $j("#matrix-div").height(window_height);

    var s = new Scheduler(data, $j("#directory-div"), $j("#matrix-div"), $j("#garbage-div"));
    s.render();
}, 
data);
