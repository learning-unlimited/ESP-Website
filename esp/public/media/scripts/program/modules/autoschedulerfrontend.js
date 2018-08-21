// This will hold the last autoscheduler run, in case we want to finalize and save it
var autoscheduler_data = '';
var stats_table_html = '';

function autoschedulerErrorHandler() {
    $j('#autoschedulerinfo').html('The server returned an error to our request. Contact your local webministry for help.');
}

function runAutoscheduler() {
    $j('#autoschedulerinfo').html('Loading...');
    var $inputs = $j('#autoschedulerform :input');
    var post_data = {'csrfmiddlewaretoken': csrf_token()};

    $inputs.each(function() {
        if(this.name.indexOf('autoscheduler_') == 0) {
            post_data[this.name] = $j(this).val();
        }
    });

    $j.ajax({
        url: "/manage/" + program_url_base + "/autoscheduler_execute",
        type: "post",
        data: post_data,
        success: function(data) {
            data = data['response'][0];
            stats_div = $j('#autoschedulerinfo');
            if (data['error_msg'])
            {
                stats_div.html("A misconfiguration or unexpected situation prevented the autoscheduler from running: " + data['error_msg']);
            }
            else
            {
                autoscheduler_data = data['autoscheduler_data'];
                stats_div.html('');
                if (data['info'].length == 0) {
                    stats_div.html("Nothing better than status quo.");
                } else {
                    stats_div.html("<h2>Warning: these have NOT been saved!</h2>");
                    var stats_table = $j("<table width='100%' cellpadding='5'>");
                    data['info'].forEach(function (entry) {
                        var stats_row = $j("<tr>");
                        entry.forEach(function (el) {
                            var stats_cell = $j("<td valign='top'>");
                            label = el[0];
                            lines = el[1];
                            stats_cell.append('<b>' + label + '</b>');
                            var bullets = $j('<ul>');
                            lines.forEach(function(line) {
                                bullets.append('<li>' + line + '</li>');
                            });
                            stats_cell.append(bullets);
                            stats_row.append(stats_cell);
                        });
                        stats_table.append(stats_row);
                    });
                    stats_div.append(stats_table);
                    stats_table_html = stats_table.html();
                    stats_div.append("<b>Hit `Save room assignments' if you are happy with this. If not, you can try playing with the parameters, or locking some sections in the AJAX scheduler (but wait a couple seconds before re-running if you do), or you can just go schedule something yourself with the AJAX scheduler. Note that these assignments will be lost if you run the automatic scheduling assistant again.</b>");
                }
            }
        },
        error: autoschedulerErrorHandler,
        dataType: 'json'
    });
}

function saveAutoscheduler() {
    $j('#autoschedulerinfo').html('Saving...');
    var post_data = {'csrfmiddlewaretoken': csrf_token(), 'autoscheduler_data': autoscheduler_data};

    $j.ajax({
        url: "/manage/" + program_url_base + "/autoscheduler_save",
        type: "post",
        data: post_data,
        success: function(data) {
            data = data['response'][0];
            stats_div = $j('#autoschedulerinfo');
            if (data['error_msg'])
            {
                stats_div.html("A misconfiguration or unexpected situation prevented the autoscheduler from running: " + data['error_msg']);
            } else {
                stats_div.html("<h2>The following scheduling assignments have been saved successfully:</h2>");
                stats_div.append(stats_table_html);
            }
        },
        error: autoschedulerErrorHandler,
        dataType: 'json'
    });
}

function clearAutoscheduler() {
    $j('#autoschedulerinfo').html('Clearing...');
    var post_data = {'csrfmiddlewaretoken': csrf_token()};
    autoscheduler_data = '';
    stats_table_html = '';

    $j.ajax({
        url: "/manage/" + program_url_base + "/autoscheduler_clear",
        type: "post",
        data: post_data,
        success: function() {
            $j('#autoschedulerinfo').html("The scheduling assignments have been cleared successfully!");
        },
        error: autoschedulerErrorHandler,
        dataType: 'json'
    });
}
