// This will hold the last autoscheduler run, in case we want to finalize and save it
var autoscheduler_data = '';

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
                    data['info'].forEach(function (el) {
                        label = el[0];
                        lines = el[1];
                        stats_div.append('<h2>' + label + '</h2>');
                        var bullets = $j('<ul>');
                        lines.forEach(function(line) {
                            bullets.append('<li>' + line + '</li>');
                        });
                        stats_div.append(bullets);
                    });
		    stats_div.append("<h2>Hit `Save room assignments' if you are happy with this.</h2>");
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
		success: function() {
			$j('#autoschedulerinfo').html("The scheduling assignments have been saved successfully!");
		},
		error: autoschedulerErrorHandler,
		dataType: 'json'
	});
}

function clearAutoscheduler() {
	$j('#autoschedulerinfo').html('Clearing...');
	var post_data = {'csrfmiddlewaretoken': csrf_token()};
    autoscheduler_data = '';

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

function toggleShowOptions(type) {
    var options = document.getElementById("autoscheduler"+type+"div");
    if (options.style.display === "none") {
	options.style.display = "block";
    } else {
	options.style.display = "none";
    }
}
