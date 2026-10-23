/**
 * An ApiClient whose requests all succeed immediately, without a server.
 */
function FakeApiClient() {
    this.get_change_log = function(index, callback, errorReporter){
        callback({changelog: [], other: []});
    };

    this.set_comment = function(section_id, comment, locked, callback, errorReporter){
        callback();
    };

    this.schedule_section = function(section_id, timeslot_ids, room_id, override, callback, errorReporter){
        callback();
    };

    this.unschedule_section = function(section_id, callback, errorReporter){
        callback();
    };

    this.swap_sections = function(assignments1, assignments2, override, callback, errorReporter){
        callback();
    };
};

module.exports = { FakeApiClient };
