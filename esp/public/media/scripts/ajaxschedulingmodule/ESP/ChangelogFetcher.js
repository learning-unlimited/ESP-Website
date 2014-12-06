function ChangelogFetcher(matrix, api_client, interval, start_index){
    this.api_client = api_client
    this.matrix = matrix

    //changelog fetching
    this.last_applied_index = start_index

    this.pollForChanges = function(){
	//TODO: configurable interval
	setInterval(this.getChanges.bind(this), 5000)
    };

    this.getChanges = function(){
	this.api_client.get_change_log(this.last_applied_index, this.applyChangeLog.bind(this))
    };

    this.applyChangeLog = function(data){
	$j.each(data.changelog, function(id, change){
	    var section_id = change.id
	    if (change.timeslots.length == 0){
		this.matrix.unscheduleSectionLocal(section_id)
	    } else {
		this.matrix.scheduleSectionLocal(section_id, change.room_name, change.timeslots)
	    }
	    this.last_applied_index = change.index
	}.bind(this))
    };
}
