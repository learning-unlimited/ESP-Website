// Wrapper for console statements
var log = function(...args) {
    if (DEBUG) console.log(...args);
};

var warn = function(...args) {
    if (DEBUG) console.warn(...args);
};

var error = function(...args) {
    if (DEBUG) console.error(...args);
};