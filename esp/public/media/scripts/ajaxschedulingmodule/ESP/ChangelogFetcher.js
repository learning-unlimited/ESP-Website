/**
 * Interacts with the server's changelog to keep the scheduler in-sync with other browsers.
 *
 * @param matrix: The matrix to apply the changes to
 * @param api_client: An API client which can interact with the server
 * @param start_index: Where to start applying changes
 *
 */
function ChangelogFetcher(matrix, api_client, start_index){
    this.api_client = api_client;
    this.matrix = matrix;

    //changelog fetching
    this.last_applied_index = start_index;

    /**
     * Poll for changes every interval milliseconds.
     *
     * @param interval: The time in milliseconds between polling the server
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
     *
     * @param data: the data to apply to the matrix
     */
    this.applyChangeLog = function(data){
        $j.each(data.changelog, function(id, change){
            var section = matrix.sections.getById(change.id);
            if (change.is_scheduling) {
                if (change.timeslots.length == 0){
                    this.matrix.sections.unscheduleSectionLocal(section);
                } else {
                    this.matrix.sections.scheduleSectionLocal(section, parseInt(change.room_name,10), change.timeslots);
                }
            } else {
                this.matrix.sections.setComment(section, change.comment, change.locked, true);
            }
            this.last_applied_index = change.index;
        }.bind(this));
    };
};
