function FakeApiClient() {
    this.schedule_section = function(a, b, c){
	return true
    }
    this.unschedule_section = function(a, b, c){
	return true
    }
}

function FakeFailingApiClient() {
    this.schedule_section = function(a, b, c){
	return false
    }
    this.unschedule_section = function(a, b, c){
	return false
    }
}
