// Dummy console object, in case Firebug is not installed
// This might break Firebug <= 1.2, but you really should've updated long ago.
if ( typeof console != 'object' ) {
    console = function() {
	function nop() { return; }
	return {
	    log: nop,
	    debug: nop,
	    info: nop,
	    warn: nop,
	    error: nop,
	    assert: nop,
	    dir: nop,
	    dirxml: nop,
	    trace: nop,
	    group: nop,
	    groupCollapsed: nop,
	    groupEnd: nop,
	    time: nop,
	    timeEnd: nop,
	    profile: nop,
	    profileEnd: nop,
	    count: nop,
	};
    }();
}

/*
 * Initialize the ESP namespace
 */
ESP = {};

ESP.declare = function(name, value) {
    name = name.split('.');
    var target = window;
    for (var i = 0; i < name.length-1; i++) {
	var n = name[i];
	if (!target[n]) target[n] = {};
	target = target[n];
    }
    name = name[name.length - 1];
    if (target[name]) {
	console.error('Redeclaration of existing namespace: ' + name + '.');
    } else {
	target[name] = value;
    }
}