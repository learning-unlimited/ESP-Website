var data = {}

json_fetch(['sections'], function(){
    s = new Scheduler(data, $j("#directory-div")[0])
    s.render()
}, 
data)
