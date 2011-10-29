
if (window.onerror) {
    window._orig_onerror_errorlog = window.onerror;
}

// An attempt at getting rid of certain googlebot JS errors which say
//     "TypeError: JSON.stringify cannot serialize cyclic structures."
// Will commit and push after seeing how effective it is.
// If you have to clobber this, also restore crashkit-javascript.js
// by running the following in /esp/esp/public/media/scripts:
//     $ patch -p0 -R < /home/pteromys/crashkit-decircularize.diff
// -ageng 2011-07-12
function uniqueObjects() {
    var seen = []
    return function (key, val) {
        if (typeof(val) == "object") {
            for (var i in seen) {
                if (val === seen[i]) { return '' + val; }
            }
            seen.push(val);
        }
        return val;
    }
}

window.onerror = function(msg, url, line)
{
    if (encodeURIComponent) {
	var uri;
	if (!url && !line && JSON) {
	    uri = "/error_reporter?url=" + encodeURIComponent(url) + "&lineNum=" + line + "&msg=" + encodeURIComponent(JSON.stringify(msg, uniqueObjects()));
	} else {
	    uri = "/error_reporter?url=" + encodeURIComponent(url) + "&lineNum=" + line + "&msg=" + encodeURIComponent(msg);
	}
        //var img = new Image();
        //img.src = uri;
    }

    if (window._orig_onerror_errorlog) {
        window._orig_onerror_errorlog(msg, url, line);
    }

    //  console.log("Got error: " + url + " line " + line + " says " + msg);
    return false;  // 'true' means "we handled the error"; 'false' passes it through to the browser's own/usual error handling mechanisms
}


