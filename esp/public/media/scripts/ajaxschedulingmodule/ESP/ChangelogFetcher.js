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
    var self = this;
    $j.getJSON('ajax_schedule_last_changed', function(data, status) {
        if (status == "success") {
            self.last_applied_index = data['latest_index'];
        }
    });

    /**
     * Poll for changes every interval milliseconds.
     *
     * @param interval: The time in milliseconds between polling the server
     */
    this.pollForChanges = function(interval){
        if (this.pollInterval) {
            window.clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        // run getChanges() immediately, then set up the recurring call
        this.getChanges();
        this.pollInterval = window.setInterval(this.getChanges.bind(this), interval);
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
        // Check if server is commanding a reload (changelog was pruned)
        if (data.other) {
            for (var i = 0; i < data.other.length; i++) {
                if (data.other[i].command === "reload") {
                    $j("#loadingOverlay").remove();
                    this.showReloadNotification();
                    return;
                }
            }
        }

        if (data.changelog) {
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
        }

        $j("#loadingOverlay").remove();
    };

    /**
     * Show a notification banner when the schedule data is out of sync.
     * Stops polling and lets the user decide when to reload.
     */
    this.showReloadNotification = function(){
        if ($j("#changelog-reload-notice").length > 0) {
            return;
        }

        var reloadLink = $j("<a>", {
            "class": "reload-link",
            href: "#",
            text: "Reload now"
        }).on("click", function(event) {
            event.preventDefault();
            window.location.reload();
        });

        var notice = $j("<div>", { id: "changelog-reload-notice" })
            .append(document.createTextNode("The schedule data is out of sync. "))
            .append(reloadLink);

        $j("body").prepend(notice);

        if (this.pollInterval) {
            window.clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    };
};
