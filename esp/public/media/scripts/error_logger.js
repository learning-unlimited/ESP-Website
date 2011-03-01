
if (window.onerror) {
    window._orig_onerror_errorlog = window.onerror;
}

window.onerror = function(msg, url, line)
{
    if (encodeURIComponent) {
        var uri = "/error_reporter?url=" + encodeURIComponent(url) + "&lineNum=" + line + "&msg=" + encodeURIComponent(msg);
        var img = new Image();
        img.src = uri;
    }

    if (window._orig_onerror_errorlog) {
        window._orig_onerror_errorlog(msg, url, line);
    }

    //  console.log("Got error: " + url + " line " + line + " says " + msg);
    return false;  // 'true' means "we handled the error"; 'false' passes it through to the browser's own/usual error handling mechanisms
}


