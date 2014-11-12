function FakeApiClient() {
    this.schedule_section = function(a, b, c, callback){
	callback();
	return true;
    };

    this.unschedule_section = function(a, callback){
	callback();
	return true;
    };
};

function FakeFailingApiClient() {
    this.schedule_section = function(a, b, c, callback){
	return false;
    };

    this.unschedule_section = function(a, callback){
	return false;
    };
};
