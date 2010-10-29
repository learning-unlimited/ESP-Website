window.onerror = function ( strErr, strURL, strLineNumber )
{
    var uri = "/error_reporter?url=" + escape(strURL) + "&lineNum=" + strLineNumber + "&msg=" + escape(strErr);
    var img = new Image();
    img.src = uri;
}


