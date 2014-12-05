function ChangelogFetcher(matrix, api_client, interval, start_index, sections){
    this.api_client = api_client
    this.matrix = matrix
    this.sections = sections

    //changelog fetching
    this.last_applied_index = 0

    this.pollForChanges = function(){
	//TODO: configurable interval
	setInterval(this.getChanges.bind(this), 5000)
    };

    this.getChanges = function(){
	this.api_client.get_change_log(this.last_applied_index, this.applyChangeLog.bind(this))
    };

    this.applyChangeLog = function(data){
	$j.each(data.changelog, function(id, change){
	    var section = this.sections[change.id]
	    if (change.timeslots.length == 0){
		this.matrix.unscheduleSectionLocal(section)
	    } else {
		this.matrix.scheduleSectionLocal(section, change.room_name, change.timeslots)
	    }
	    this.last_applied_index = change.index
	}.bind(this))
    };
}
