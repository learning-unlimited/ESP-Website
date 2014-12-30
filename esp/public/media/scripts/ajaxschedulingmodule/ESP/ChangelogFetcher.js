function ChangelogFetcher(matrix, api_client, start_index){
    this.api_client = api_client;
    this.matrix = matrix;

    //changelog fetching
    this.last_applied_index = start_index;

    /**
     * Poll for changes every interval ms.
     */
    this.pollForChanges = function(interval){
	    window.setInterval(this.getChanges.bind(this), interval);
    };

    /**
     * Fetch the changelog from the server
     */
    this.getChanges = function(){
	    this.api_client.get_change_log(
	        this.last_applied_index,
	        this.applyChangeLog.bind(this),
	        function(msg) {
		        console.log(msg);
	        }
	    );
    };

    /**
     * Apply the changes locally
     */
    this.applyChangeLog = function(data){
	    $j.each(data.changelog, function(id, change){
	        var section_id = change.id;
	        if (change.timeslots.length == 0){
		        this.matrix.sections.unscheduleSectionLocal(section_id);
	        } else {
		        this.matrix.sections.scheduleSectionLocal(section_id, change.room_name, change.timeslots);
	        }
	        this.last_applied_index = change.index;
	    }.bind(this));
    };
};
