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