// This will hold the last lottery run, in case we want to finalize and save it
var lottery_data = '';

// Interval to update UI showing "progress" while performing lottery actions.
var lottery_progress_interval = null;

function lotteryErrorHandler() {
	clearInterval(lottery_progress_interval);
	$j('#lotteryStats').html('The server returned an error to our request. Contact your local webministry for help.');
}

function startUpdatingLotteryProgress() {
	lottery_progress_interval = setInterval(function() {
		var stats_div = $j('#lotteryStats');
		var text = stats_div.text();
		var dots = 0;
		for(var i = 0; i < text.length; i++) {
			if(text[i] == '.') {
				dots++;
			}
		}
		if(dots < 5) {
			stats_div.text(text + '.');
		} else {
			stats_div.text(text.replace(/\./g, '') + '..');
		}
	}, 500);
}

$j(document).ready(function() {
	$j('#lotteryForm').submit(function(e) {
		e.preventDefault();
		var $inputs = $j('#lotteryForm :input');
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
				clearInterval(lottery_progress_interval);

				data = data['response'][0];
				var stats_div = $j('#lotteryStats');
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
					$j('.lotterySave').prop('disabled', false);
				}
			},
			error: lotteryErrorHandler,
			dataType: 'json'
		});

		$j('#lotteryStats').html('Loading...');
		startUpdatingLotteryProgress();
		$j('.lotterySave').prop('disabled', true);
	});

	$j('.lotterySave').click(function() {
		var post_data = {'csrfmiddlewaretoken': csrf_token(), 'lottery_data': lottery_data};

		$j.ajax({
			url: "/manage/" + program_url_base + "/lottery_save",
			type: "post",
			data: post_data,
			success: function() {
				clearInterval(lottery_progress_interval);
				$j('#lotteryStats').html("The student schedules have been saved successfully!");
			},
			error: lotteryErrorHandler,
			dataType: 'json'
		});

		$j('#lotteryStats').html('Saving...');
		startUpdatingLotteryProgress();

		$j('.lotterySave').prop('disabled', true);
		$j('#lotterySaveSafe').css('display', 'none');
		$j('#lotterySaveOverwrite').css('display', 'inline');
	});
});
