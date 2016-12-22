// This will hold the last lottery run, in case we want to finalize and save it
var lottery_data = '';

function lotteryErrorHandler() {
	$j('#lotterythingstats').html('The server returned an error to our request. Contact your local webministry for help.');
}

function runLotteryThing() {
	$j('#lotterythingstats').html('Loading...');
	var $inputs = $j('#lotteryform :input');
	var post_data = {'csrfmiddlewaretoken': csrf_token()};

	$inputs.each(function() {
		if(this.name.indexOf('lottery_') == 0) {
			post_data[this.name] = $j(this).val();
		}
	});

	$j.ajax({
		url: "/manage/" + program_url_base + "/lottery_execute",
		type: "post",
		data: post_data,
		success: function(data) {
			data = data['response'][0];
			stats_div = $j('#lotterythingstats');
			if (data['error_msg'])
			{
				stats_div.html("A misconfiguration or unexpected situation prevented the lottery from running: " + data['error_msg']);
			}
			else
			{
				lottery_data = data['lottery_data'];
				stats_div.html('');
				data['stats'].forEach(function (el) {
					label = el[0];
					lines = el[1];
					stats_div.append('<h2>' + label + '</h2>');
					var bullets = $j('<ul>');
					lines.forEach(function(line) {
						bullets.append('<li>' + line + '</li>');
					});
					stats_div.append(bullets);
				});
			}
		},
		error: lotteryErrorHandler,
		dataType: 'json'
	});
}

function saveLotteryThing() {
	$j('#lotterythingstats').html('Saving...');
	var post_data = {'csrfmiddlewaretoken': csrf_token(), 'lottery_data': lottery_data};

	$j.ajax({
		url: "/manage/" + program_url_base + "/lottery_save",
		type: "post",
		data: post_data,
		success: function() {
			$j('#lotterythingstats').html("The lottery assignments has been saved successfully!");
		},
		error: lotteryErrorHandler,
		dataType: 'json'
	});
}

function clearLotteryThing() {
	$j('#lotterythingstats').html('Clearing...');
	var post_data = {'csrfmiddlewaretoken': csrf_token()};

	$j.ajax({
		url: "/manage/" + program_url_base + "/lottery_clear",
		type: "post",
		data: post_data,
		success: function() {
			$j('#lotterythingstats').html("The lottery assignments have been cleared successfully!");
		},
		error: lotteryErrorHandler,
		dataType: 'json'
	});
}
