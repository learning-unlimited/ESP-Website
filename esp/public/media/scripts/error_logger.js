
window.onerror = function(msg, url, line)
{
    var uri = "/error_reporter?url=" + escape(url) + "&lineNum=" + line + "&msg=" + escape(msg);
    var img = new Image();
    img.src = uri;

    //  console.log("Got error: " + url + " line " + line + " says " + msg);
    return true;
}


