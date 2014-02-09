var data = {}

json_fetch(['sections', 'timeslots', 'rooms'], function(){
    s = new Scheduler(data, $j("#directory-div")[0], $j("#matrix-div")[0])
    s.render()
}, 
data)
