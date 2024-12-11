/**
 * Interacts with the server's changelog to keep the scheduler in-sync with other browsers.
 *
 * @param matrix: The matrix to apply the changes to
 * @param api_client: An API client which can interact with the server
 *
 */
function ChangelogFetcher(matrix, api_client){
    this.api_client = api_client;
    this.matrix = matrix;

    // Get the index of the last change in the changelog
    this.last_applied_index = 0;
    $j.getJSON('ajax_schedule_last_changed', function(data, status) {
        if (status == "success") {
            this.last_applied_index = data['latest_index'];
        }
    });

    /**
     * Poll for changes every interval milliseconds.
     *
     * @param interval: The time in milliseconds between polling the server
     */
    this.pollForChanges = function(interval){
        // run getChanges() immediately, then set up the recurring call
        this.getChanges();
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
            } else if (change.is_moderator) {
                this.matrix.moderatorDirectory.selectModerator(this.matrix.moderatorDirectory.getById(change.moderator));
                if (change.assigned) {
                    this.matrix.moderatorDirectory.assignModeratorLocal(section);
                } else {
                    this.matrix.moderatorDirectory.unassignModeratorLocal(section);
                }
            } else {
                this.matrix.sections.setComment(section, change.comment, change.locked, true);
            }
            this.last_applied_index = change.index;
        }.bind(this));
        $j("#loadingOverlay").remove(); // remove the loading overlay
    };
};
