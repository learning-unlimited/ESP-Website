/* Set up jQuery and shortcuts */
$j = $.noConflict();

$j.getScriptWithCaching = function(url, callback, cache){
// Like getScript, but doesn't do cache busting
$j.ajax({
        type: "GET",
        url: url,
        success: callback,
        dataType: "script",
        cache: true
});
};
