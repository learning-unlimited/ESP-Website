// This will hold the last lottery run, in case we want to finalize and save it
var lottery_data = '';

// Interval to update UI showing "progress" while performing lottery actions.
var lottery_progress_interval = null;

// Legacy vs ILP mode boxes: only the active one is expanded.
function setLotteryMode(mode) {
	$j('.lottery-mode-box').removeClass('active');
	$j('.lottery-mode-box[data-lottery-mode="' + mode + '"]').addClass('active');
}

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
				if(this.type == 'checkbox') {
					post_data[this.name] = this.checked ? 'True' : 'False';
				} else {
					post_data[this.name] = $j(this).val();
				}
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
					data['charts'].forEach(function (el, index) {
						canvas_id='chart'+index;
						stats_div.append('<canvas id="'+canvas_id+'" height="300" width="500" style="height:300px; width:500px;"></canvas>');
						new Chart(document.getElementById(canvas_id),el);
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

// ----------------------------------------------------------------------
// ILP lottery: async runs, polled via lottery_ilp_status.
// ----------------------------------------------------------------------

var ilp_poll_interval = null;

// Preserved across renderILPRuns() calls, so expand state / fetched stats /
// dropdown open-state survive a poll tick.
var ilp_last_runs = [];
var ilp_expanded_run_ids = {};
var ilp_run_stats_cache = {};
var ilp_last_status_by_run = {};
var ilp_text_stats_open = {};
var ilp_settings_open = {};
var ilp_progress_values_open = {};

// Per-run persistent DOM node registry -- run rows (and their detail rows,
// once built) are created once and updated in place on later polls, rather
// than the whole #ilpRunsBody being emptied and rebuilt from scratch every
// 2s.
var ilp_row_state = {};

function formatILPProgressValues(run) {
	if (!run.progress || run.progress.length === 0) {
		return 'none yet';
	}
	var last = run.progress[run.progress.length - 1];
	var incumbent = (last.incumbent === null || last.incumbent === undefined) ? 'none yet' : last.incumbent.toFixed(2);
	var bound = (last.bound === null || last.bound === undefined) ? 'n/a' : last.bound.toFixed(2);
	return 'best=' + incumbent + ' bound=' + bound;
}

function formatILPTimestamp(iso) {
	if (!iso) { return ''; }
	var d = new Date(iso);
	function pad(n) { return (n < 10 ? '0' : '') + n; }
	return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' +
		pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
}

var ILP_TERMINAL_STATUSES = {'done': true, 'interrupted': true, 'failed': true};
var ILP_STATS_READY_STATUSES = {'done': true, 'interrupted': true};

function formatILPStatus(run) {
	if (!run.submitted_at) { return run.status; }
	var terminal = !!ILP_TERMINAL_STATUSES[run.status];
	var startMs = new Date(run.submitted_at).getTime();
	var endMs = terminal ? (run.finished_at ? new Date(run.finished_at).getTime() : null) : Date.now();
	if (endMs === null) { return run.status; }
	var secs = Math.max(0, (endMs - startMs) / 1000);
	return run.status + (terminal ? ' after ' : ' for ') + secs.toFixed(1) + 's';
}

function fetchILPRunStats(runId) {
	$j.ajax({
		url: "/manage/" + program_url_base + "/lottery_ilp_stats",
		type: "post",
		data: {'csrfmiddlewaretoken': csrf_token(), 'run_id': runId},
		success: function(data) {
			var item = data['response'][0];
			ilp_run_stats_cache[runId] = item.error_msg ? {error: item.error_msg} : {stats: item.stats, charts: item.charts};
			renderILPRuns(ilp_last_runs);
		},
		error: function() {
			ilp_run_stats_cache[runId] = {error: 'Could not load stats.'};
			renderILPRuns(ilp_last_runs);
		},
		dataType: 'json'
	});
}

function toggleILPRunExpand(runId) {
	if (ilp_expanded_run_ids[runId]) {
		delete ilp_expanded_run_ids[runId];
	} else {
		ilp_expanded_run_ids[runId] = true;
		var run = ilp_last_runs.filter(function(r) { return r.id === runId; })[0];
		if (run && ILP_STATS_READY_STATUSES[run.status] && !ilp_run_stats_cache[runId]) {
			fetchILPRunStats(runId);
		}
	}
	renderILPRuns(ilp_last_runs);
}

// Draws each bar's value above the bar -- Chart.js core has no built-in
// data-label support, so this is a small per-chart plugin instead of
// pulling in an external plugin library.
var ilpBarValueLabelPlugin = {
	id: 'ilpBarValueLabel',
	afterDatasetsDraw: function(chart) {
		var ctx = chart.ctx;
		ctx.save();
		ctx.fillStyle = '#333';
		ctx.font = '11px sans-serif';
		ctx.textAlign = 'center';
		ctx.textBaseline = 'bottom';
		chart.data.datasets.forEach(function(dataset, datasetIndex) {
			var meta = chart.getDatasetMeta(datasetIndex);
			meta.data.forEach(function(bar, index) {
				var value = dataset.data[index];
				ctx.fillText(value, bar.x, bar.y - 4);
			});
		});
		ctx.restore();
	}
};

// Gurobi stops as soon as EITHER MIPGapAbs or MIPGap*|incumbent| is
// satisfied (OR, not AND) -- so the threshold that actually determines when
// the run will stop is whichever of the two is currently LARGER (the gap
// will cross that one first as it shrinks). Recomputed from the latest
// incumbent each time, not stored -- so the line is always "as of now".
function computeILPGapThreshold(run) {
	if (!run.progress || run.progress.length === 0) {
		return null;
	}
	var last = run.progress[run.progress.length - 1];
	if (last.incumbent === null || last.incumbent === undefined) {
		return null;
	}
	var solve = (run.params && run.params.solve) || {};
	// Gurobi's own defaults, used if the run didn't set these explicitly.
	var mipGapAbs = (solve.MIPGapAbs !== undefined && solve.MIPGapAbs !== null) ? solve.MIPGapAbs : 1e-10;
	var mipGapRel = (solve.MIPGap !== undefined && solve.MIPGap !== null) ? solve.MIPGap : 1e-4;
	var relThreshold = mipGapRel * Math.abs(last.incumbent);
	return Math.max(mipGapAbs, relThreshold);
}

// Point-computation only, shared by chart creation and later incremental
// updates. Returns {points, maxT}, or null if there's nothing plottable yet.
function computeILPProgressChartPoints(run) {
	var points = [];
	var EPSILON = 1e-9; // prevent us from trying to plot a 0 on a log scale
	(run.progress || []).forEach(function(entry) {
		var gap = entry.gap_abs;
		if (gap === null || gap === undefined) {
			if (entry.incumbent === null || entry.incumbent === undefined ||
				entry.bound === null || entry.bound === undefined) {
				return;
			}
			gap = Math.abs(entry.incumbent - entry.bound);
		}
		var t = entry.start_runtime;
		if (t === null || t === undefined) {
			return;
		}
		var y = Math.max(gap, EPSILON);
		points.push({x: t, y: y});
		var endT = entry.end_runtime;
		if (endT !== null && endT !== undefined && endT > t) {
			points.push({x: endT, y: y});
		}
	});
	if (points.length === 0) {
		return null;
	}
	return {points: points, maxT: points[points.length - 1].x};
}

// Chart.js config for creation only -- later updates patch the existing
// instance's data/scales in place (see updateILPProgressChart()) rather
// than rebuilding, so this shape only needs to match on first construction.
function buildILPProgressChartConfig(points, maxT, thresholdY) {
	var datasets = [{
		data: points,
		label: 'gap (|best - bound|)',
		borderColor: '#456900',
		backgroundColor: '#456900',
		pointRadius: 2,
		fill: false,
		stepped: true,
	}];
	if (thresholdY !== null) {
		datasets.push({
			data: [{x: 0, y: thresholdY}, {x: maxT, y: thresholdY}],
			label: 'stop threshold',
			borderColor: '#999',
			borderDash: [5, 5],
			pointRadius: 0,
			fill: false,
		});
	}
	return {
		type: 'line',
		data: {datasets: datasets},
		options: {
			responsive: false,
			animation: false,
			events: [],
			plugins: {
				legend: {display: thresholdY !== null},
				title: {display: true, text: 'Optimality gap over time'},
			},
			scales: {
				x: {type: 'linear', max: maxT, title: {display: true, text: 'runtime (s)'}},
				y: {type: 'logarithmic', title: {display: true, text: 'gap'}},
			},
		},
	};
}

function updateILPProgressChart(state, run) {
	var computed = computeILPProgressChartPoints(run);
	if (!computed) {
		if (!state.progressChart) {
			state.$progressPlaceholder.text('No progress data yet.').show();
		}
		return;
	}

	var threshold = computeILPGapThreshold(run);
	var thresholdY = threshold !== null ? Math.max(threshold, 1e-9) : null;

	if (!state.progressChart) {
		state.$progressPlaceholder.hide();
		var canvas_id = 'ilpProgressChart_' + run.id;
		state.$progressCanvas = $j('<canvas id="' + canvas_id + '" height="400" width="500" style="height:400px; width:500px;"></canvas>');
		state.$progressChartArea.append(state.$progressCanvas);
		state.progressChart = new Chart(
			document.getElementById(canvas_id),
			buildILPProgressChartConfig(computed.points, computed.maxT, thresholdY)
		);
	} else {
		var chart = state.progressChart;
		chart.data.datasets[0].data = computed.points;
		if (thresholdY !== null) {
			var thresholdData = [{x: 0, y: thresholdY}, {x: computed.maxT, y: thresholdY}];
			if (chart.data.datasets.length > 1) {
				chart.data.datasets[1].data = thresholdData;
			} else {
				chart.data.datasets.push({
					data: thresholdData,
					label: 'stop threshold',
					borderColor: '#999',
					borderDash: [5, 5],
					pointRadius: 0,
					fill: false,
				});
			}
			chart.options.plugins.legend.display = true;
		} else if (chart.data.datasets.length > 1) {
			chart.data.datasets.pop();
			chart.options.plugins.legend.display = false;
		}
		chart.options.scales.x.max = computed.maxT;
		chart.update();
	}

	if (ILP_STATS_READY_STATUSES[run.status] && !state.chartMovedInside) {
		state.$progressCanvas.insertAfter(state.$progressDetails.find('summary'));
		state.chartMovedInside = true;
	}
}

// Builds the detail cell's structure exactly once (on first expand). Called
// again on later polls only to update the specific pieces whose data can
// actually change -- see updateILPRunDetail(). Most of this (settings JSON,
// final stats/charts) never changes again after being built, so there's
// nothing to "keep in sync" for it at all, let alone a reason to rebuild it.
function buildILPRunDetailSkeleton(state, run) {
	var $detailCell = state.$detailCell;

	state.$errorP = $j('<p style="color:#a00;">').hide();
	$detailCell.append(state.$errorP);

	// Chart lives directly in the cell while running (live, front and
	// center); relocated into the dropdown once finished -- see
	// updateILPProgressChart().
	state.$progressChartArea = $j('<div>');
	state.$progressPlaceholder = $j('<p>').hide();
	state.$progressChartArea.append(state.$progressPlaceholder);
	$detailCell.append(state.$progressChartArea);
	state.progressChart = null;
	state.chartMovedInside = false;

	state.$progressDetails = $j('<details>');
	if (ilp_progress_values_open[run.id]) {
		state.$progressDetails.prop('open', true);
	}
	state.$progressDetails.on('toggle', function() {
		ilp_progress_values_open[run.id] = this.open;
	});
	state.$progressDetails.append($j('<summary>').text('Progress values'));
	state.$progressValuesP = $j('<p>');
	state.$progressDetails.append(state.$progressValuesP);
	$detailCell.append(state.$progressDetails);

	state.$statsArea = $j('<div>');
	$detailCell.append(state.$statsArea);
	state.statsBuilt = false;

	var $settingsDetails = $j('<details>');
	if (ilp_settings_open[run.id]) {
		$settingsDetails.prop('open', true);
	}
	$settingsDetails.on('toggle', function() {
		ilp_settings_open[run.id] = this.open;
	});
	$settingsDetails.append($j('<summary>').text('Settings'));

	state.$labelInput = $j('<input type="text" class="input-small ilp-label-input">').val(run.label || '');
	state.$labelInput.on('blur', function() {
		var newLabel = state.$labelInput.val();
		if (newLabel === state.lastKnownLabel) { return; }
		relabelILPRun(run.id, newLabel);
	});
	state.$labelInput.on('keydown', function(e) {
		if (e.which === 13) { state.$labelInput.blur(); }
	});
	var $labelP = $j('<p>').append($j('<label>').text('Label: '));
	$labelP.append(state.$labelInput);
	$settingsDetails.append($labelP);

	// run.params never changes after submit -- built once, no update path.
	$settingsDetails.append(
		$j('<pre>').css('white-space', 'pre-wrap').text(JSON.stringify(run.params || {}, null, 2))
	);
	$detailCell.append($settingsDetails);

	state.lastKnownLabel = run.label || '';
}

// Called every poll while the row is expanded. Builds the skeleton once,
// then only touches the fields that can actually change: error text,
// progress chart/values (live while running), and whether the final stats
// section has arrived yet (built once, then left alone). The label input's
// value is the one field synced from the server that's also user-editable,
// so it's the one place a "don't clobber it while focused" check is
// actually meaningful -- same as any controlled-input pattern, not specific
// to this codebase.
function updateILPRunDetail(state, run) {
	if (!state.built) {
		buildILPRunDetailSkeleton(state, run);
		state.built = true;
	}

	if (run.error) {
		state.$errorP.text(run.error).show();
	} else {
		state.$errorP.hide();
	}

	updateILPProgressChart(state, run);
	state.$progressValuesP.text(formatILPProgressValues(run));

	if (!state.statsBuilt) {
		if (!ILP_STATS_READY_STATUSES[run.status]) {
			state.$statsArea.empty().append($j('<p>').text('Stats will be available once this run finishes.'));
		} else {
			var cached = ilp_run_stats_cache[run.id];
			if (!cached) {
				state.$statsArea.empty().append($j('<p>').text('Loading stats…'));
			} else if (cached.error) {
				state.$statsArea.empty().append($j('<p>').text(cached.error));
				state.statsBuilt = true; // terminal error, nothing more will arrive
			} else {
				state.$statsArea.empty();
				// Plots shown by default; the text breakdown is behind its
				// own further dropdown.
				(cached.charts || []).forEach(function(el, index) {
					var canvas_id = 'ilpChart_' + run.id + '_' + index;
					state.$statsArea.append('<canvas id="' + canvas_id + '" height="300" width="500" style="height:300px; width:500px;"></canvas>');
					var config = $j.extend(true, {}, el);
					config.plugins = [ilpBarValueLabelPlugin];
					new Chart(document.getElementById(canvas_id), config);
				});

				var $statsDetails = $j('<details>');
				if (ilp_text_stats_open[run.id]) {
					$statsDetails.prop('open', true);
				}
				$statsDetails.on('toggle', function() {
					ilp_text_stats_open[run.id] = this.open;
				});
				$statsDetails.append($j('<summary>').text('Text stats'));
				(cached.stats || []).forEach(function(el) {
					var label = el[0], lines = el[1];
					$statsDetails.append($j('<h4>').text(label));
					var $ul = $j('<ul>');
					lines.forEach(function(line) { $ul.append($j('<li>').text(line)); });
					$statsDetails.append($ul);
				});
				state.$statsArea.append($statsDetails);
				state.statsBuilt = true; // final numbers -- nothing more to update, ever
			}
		}
	}

	if (document.activeElement !== state.$labelInput[0]) {
		state.$labelInput.val(run.label || '');
	}
	state.lastKnownLabel = run.label || '';
}

function updateILPRunRow(state, run, hasAnyLabel) {
	var $row = state.$row;
	$row.empty();

	var terminal = !!ILP_TERMINAL_STATUSES[run.status];
	var expanded = !!ilp_expanded_run_ids[run.id];

	var $expandCell = $j('<td style="cursor:pointer;">').text(expanded ? '▼' : '▶');
	$expandCell.click(function() { toggleILPRunExpand(run.id); });
	$row.append($expandCell);

	$row.append($j('<td>').text(run.id));
	if (hasAnyLabel) {
		$row.append($j('<td>').text(run.label || ''));
	}
	$row.append($j('<td>').text(formatILPStatus(run)));
	$row.append($j('<td>').text(formatILPTimestamp(run.submitted_at)));

	var $actions = $j('<td>');
	if (!terminal) {
		var $stopBtn = $j('<button type="button" class="btn btn-warning btn-small custom-action">Interrupt</button>');
		$stopBtn.click(function() { stopILPRun(run.id); });
		$actions.append($stopBtn);
	} else {
		var $saveBtn = $j('<button type="button" class="btn btn-success btn-small custom-action">Save</button>');
		if (!run.has_result) {
			$saveBtn.prop('disabled', true).css({'opacity': '0.5', 'color': '#666'});
		}
		if (run.saved_at) {
			$saveBtn.text('Saved');
		}
		$saveBtn.click(function() { saveILPRun(run.id); });
		$actions.append($saveBtn);

		var $archiveBtn = $j('<button type="button" class="btn btn-small custom-action" style="margin-left:5px;">Archive</button>');
		$archiveBtn.click(function() { archiveILPRun(run.id); });
		$actions.append($archiveBtn);
	}
	$row.append($actions);
}

function removeILPRunRow(runId) {
	var state = ilp_row_state[runId];
	if (!state) { return; }
	state.$row.remove();
	if (state.$detailRow) { state.$detailRow.remove(); }
	delete ilp_row_state[runId];
}

function renderILPRuns(runs) {
	ilp_last_runs = runs;

	runs.forEach(function(run) {
		var prevStatus = ilp_last_status_by_run[run.id];
		if (prevStatus !== undefined && prevStatus !== run.status && ILP_STATS_READY_STATUSES[run.status]) {
			delete ilp_run_stats_cache[run.id];
			if (ilp_expanded_run_ids[run.id]) {
				fetchILPRunStats(run.id);
			}
		}
		ilp_last_status_by_run[run.id] = run.status;
	});

	var $tbody = $j('#ilpRunsBody');
	var hasAnyLabel = runs.some(function(run) { return run.label; });
	$j('#ilpLabelHeader').toggle(hasAnyLabel);
	var colspan = hasAnyLabel ? 6 : 5;

	if (runs.length === 0) {
		Object.keys(ilp_row_state).forEach(removeILPRunRow);
		$tbody.empty();
		$tbody.append('<tr class="ilp-no-runs-row"><td colspan="' + colspan + '">No runs yet.</td></tr>');
		return;
	}
	$tbody.find('.ilp-no-runs-row').remove();

	// Drop rows for runs no longer in the list (e.g. archived).
	var incomingIds = {};
	runs.forEach(function(run) { incomingIds[run.id] = true; });
	Object.keys(ilp_row_state).forEach(function(idStr) {
		if (!incomingIds[idStr]) { removeILPRunRow(idStr); }
	});

	// Iterate oldest-to-newest (reverse of the server's newest-first order)
	// so that prepending each newly-seen run individually still ends up
	// newest-on-top overall. Prepending in the server's own (newest-first)
	// order gets this backwards whenever more than one run is new in the
	// same poll -- e.g. incoming [B, A] (B newer) would prepend B first
	// (tbody: [B]), then prepend A on top of that (tbody: [A, B]) --
	// reversed. This isn't a rare case: it's every page load, since every
	// run is "new" to the client at once then.
	runs.slice().reverse().forEach(function(run) {
		var state = ilp_row_state[run.id];
		if (!state) {
			state = {$row: $j('<tr>'), $detailRow: null, $detailCell: null, built: false};
			ilp_row_state[run.id] = state;
			$tbody.prepend(state.$row);
		}

		updateILPRunRow(state, run, hasAnyLabel);

		var expanded = !!ilp_expanded_run_ids[run.id];
		if (expanded) {
			if (!state.$detailRow) {
				state.$detailRow = $j('<tr>');
				state.$detailCell = $j('<td style="background:#f8f8f8;">');
				state.$detailRow.append(state.$detailCell);
				state.$row.after(state.$detailRow);
			}
			// colspan can change poll-to-poll (hasAnyLabel toggling), so
			// keep it in sync even though the cell itself is persistent.
			state.$detailCell.attr('colspan', colspan);
			updateILPRunDetail(state, run);
			state.$detailRow.show();
		} else if (state.$detailRow) {
			state.$detailRow.hide();
		}
	});
}

function pollILPStatus() {
	$j.ajax({
		url: "/manage/" + program_url_base + "/lottery_ilp_status",
		type: "post",
		data: {'csrfmiddlewaretoken': csrf_token()},
		success: function(data) {
			renderILPRuns(data['response'][0]['runs']);
		},
		dataType: 'json'
	});
	// Piggybacks on the same 2s cadence while the dropdown is open, so it
	// keeps updating live (e.g. if another tab archives/unarchives a run)
	// instead of only refreshing at open-time.
	var archivedDetailsEl = $j('#ilpArchivedRunsDetails')[0];
	if (archivedDetailsEl && archivedDetailsEl.open) {
		fetchILPArchivedRuns();
	}
}

function relabelILPRun(run_id, label) {
	$j.ajax({
		url: "/manage/" + program_url_base + "/lottery_ilp_relabel",
		type: "post",
		data: {'csrfmiddlewaretoken': csrf_token(), 'run_id': run_id, 'label': label},
		success: function(data) {
			var item = data['response'][0];
			if (item.error_msg) { alert(item.error_msg); }
			pollILPStatus();
		},
		dataType: 'json'
	});
}

function stopILPRun(run_id) {
	$j.ajax({
		url: "/manage/" + program_url_base + "/lottery_ilp_stop",
		type: "post",
		data: {'csrfmiddlewaretoken': csrf_token(), 'run_id': run_id},
		success: function(data) {
			var item = data['response'][0];
			if (item.error_msg) { alert(item.error_msg); }
			pollILPStatus();
		},
		dataType: 'json'
	});
}

function saveILPRun(run_id) {
	if (!confirm("Save this run's assignments to the website? This will overwrite any existing schedules.")) {
		return;
	}
	$j.ajax({
		url: "/manage/" + program_url_base + "/lottery_ilp_save",
		type: "post",
		data: {'csrfmiddlewaretoken': csrf_token(), 'run_id': run_id},
		success: function(data) {
			var item = data['response'][0];
			if (item.error_msg) { alert(item.error_msg); }
			pollILPStatus();
		},
		dataType: 'json'
	});
}

function archiveILPRun(run_id) {
	$j.ajax({
		url: "/manage/" + program_url_base + "/lottery_ilp_archive",
		type: "post",
		data: {'csrfmiddlewaretoken': csrf_token(), 'run_id': run_id},
		success: function(data) {
			var item = data['response'][0];
			if (item.error_msg) { alert(item.error_msg); }
			pollILPStatus();
		},
		dataType: 'json'
	});
}

function fetchILPArchivedRuns() {
	$j.ajax({
		url: "/manage/" + program_url_base + "/lottery_ilp_archived_status",
		type: "post",
		data: {'csrfmiddlewaretoken': csrf_token()},
		success: function(data) {
			renderILPArchivedRuns(data['response'][0]['runs']);
		},
		dataType: 'json'
	});
}

function renderILPArchivedRuns(runs) {
	var $tbody = $j('#ilpArchivedRunsBody');
	$tbody.empty();
	if (runs.length === 0) {
		$tbody.append('<tr><td colspan="5">No archived runs.</td></tr>');
		return;
	}
	runs.forEach(function(run) {
		var $row = $j('<tr>');
		$row.append($j('<td>').text(run.id));
		$row.append($j('<td>').text(run.label || ''));
		$row.append($j('<td>').text(formatILPStatus(run)));
		$row.append($j('<td>').text(formatILPTimestamp(run.submitted_at)));
		var $unarchiveBtn = $j('<button type="button" class="btn btn-small custom-action">Unarchive</button>');
		$unarchiveBtn.click(function() { unarchiveILPRun(run.id); });
		$row.append($j('<td>').append($unarchiveBtn));
		$tbody.append($row);
	});
}

function unarchiveILPRun(run_id) {
	$j.ajax({
		url: "/manage/" + program_url_base + "/lottery_ilp_unarchive",
		type: "post",
		data: {'csrfmiddlewaretoken': csrf_token(), 'run_id': run_id},
		success: function(data) {
			var item = data['response'][0];
			if (item.error_msg) { alert(item.error_msg); }
			fetchILPArchivedRuns();
			pollILPStatus();
		},
		dataType: 'json'
	});
}

// ILP form validation, mirroring the parameter checks in
// ILPLotteryAssignmentController (esp/program/controllers/lottery/ilp.py) so a
// typo is caught here rather than after the server has loaded every
// registration to build the model. Only checks that need nothing but the form
// values live here; those needing program data (penalty keys vs.
// num_timeslots, per-section capacities) are still left to the server.

function addILPError(errors, $field, msg) {
	errors.push({$field: $field, msg: msg});
}

// parseFloat('1.5nonsense') === 1.5, which is too forgiving for a form check.
function ilpParseNumber(value) {
	var trimmed = $j.trim(value || '');
	return /^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$/.test(trimmed) ? parseFloat(trimmed) : NaN;
}

function isILPNumber(value) {
	return typeof value === 'number' && isFinite(value);
}

// Both penalty fields come down to a list of [x, penalty] points whose penalty
// is never negative and never rises; only the rules on x differ.
function validateILPPenaltyPoints(points, errors, $field, label, rising) {
	for (var i = 0; i < points.length; i++) {
		if (!isILPNumber(points[i][1]) || points[i][1] < 0) {
			return addILPError(errors, $field, label + ' must all be numbers that are at least 0.');
		}
		if (i > 0 && points[i][1] > points[i - 1][1]) {
			return addILPError(errors, $field, label + ' must never increase ' + rising + '.');
		}
	}
}

// {"0": 1000, "1": 100, "2": 20}: filled timeslots -> penalty points.
function validateILPStudentPenalties($field, value, errors) {
	if (value === null || typeof value !== 'object' || $j.isArray(value)) {
		return addILPError(errors, $field, 'Empty schedule penalties must be a JSON object, e.g. {"0": 1000, "1": 100, "2": 20}.');
	}
	var keys = [];
	for (var key in value) {
		if (Object.prototype.hasOwnProperty.call(value, key)) { keys.push($j.trim(key)); }
	}
	if (keys.length === 0) { return; }  // the server falls back to its default
	keys.sort(function(a, b) { return a - b; });

	// A key that isn't listed counts as a penalty of 0 on the server, so a gap
	// (e.g. {"0": 1000, "2": 20}) trips its monotonicity check even though the
	// listed values look fine. Require the keys to run 0, 1, 2, ... instead.
	var points = [];
	for (var i = 0; i < keys.length; i++) {
		if (!/^\d+$/.test(keys[i]) || parseInt(keys[i], 10) !== i) {
			return addILPError(errors, $field, 'Empty schedule penalty keys must be whole numbers of filled timeslots running 0, 1, 2, ... with none skipped.');
		}
		points.push([i, value[keys[i]]]);
	}
	validateILPPenaltyPoints(points, errors, $field, 'Empty schedule penalties', 'as more timeslots are filled');
}

// [[0, 1000], [0.3, 100], [0.5, 0], [1, 0]]: fraction of capacity -> penalty points.
function validateILPSectionPoints($field, value, errors) {
	if (!$j.isArray(value) || value.length < 2) {
		return addILPError(errors, $field, 'Empty section penalties must be a JSON list of at least two [fraction, penalty] pairs, e.g. [[0, 1000], [0.5, 0], [1, 0]].');
	}
	for (var i = 0; i < value.length; i++) {
		if (!$j.isArray(value[i]) || value[i].length !== 2 || !isILPNumber(value[i][0])) {
			return addILPError(errors, $field, 'Every empty section penalty entry must be a pair of numbers, [fraction of capacity, penalty points].');
		}
		if (i > 0 && value[i][0] <= value[i - 1][0]) {
			return addILPError(errors, $field, 'Empty section penalty fractions must strictly increase.');
		}
	}
	// A negative fraction can only appear before the required 0, so this
	// covers ilp.py's non-negative check too.
	if (value[0][0] !== 0 || value[value.length - 1][0] !== 1) {
		return addILPError(errors, $field, 'Empty section penalties must start at fraction 0 and end at fraction 1.');
	}
	validateILPPenaltyPoints(value, errors, $field, 'Empty section penalties', 'as the section fills up');
}

function clearILPFormErrors() {
	$j('#ilpFormErrors').hide().empty();
	$j('#ilpSubmitForm .ilp-field-error').removeClass('ilp-field-error');
}

function showILPFormErrors(errors) {
	var $list = $j('<ul>');
	var seen = {};
	for (var i = 0; i < errors.length; i++) {
		if (errors[i].$field) { errors[i].$field.addClass('ilp-field-error'); }
		// Several fields can hit the same problem (e.g. three blank rank
		// weights); highlight each one but only list the message once.
		if (seen[errors[i].msg]) { continue; }
		seen[errors[i].msg] = true;
		$list.append($j('<li>').text(errors[i].msg));
	}
	var $box = $j('#ilpFormErrors');
	$box.empty()
		.append($j('<strong>').text('Fix these before submitting:'))
		.append($list)
		.show();
	if ($box[0] && $box[0].scrollIntoView) { $box[0].scrollIntoView(); }
}

$j(document).ready(function() {
	var $ilpForm = $j('#ilpSubmitForm');
	if ($ilpForm.length === 0) {
		return; // ILP lottery isn't available/configured on this server
	}

	$j('#ilpArchivedRunsDetails').on('toggle', function() {
		if (this.open) {
			fetchILPArchivedRuns();
		}
	});

	function updateDeweightFactorVisibility() {
		var method = $j('#ilpDeweightMethod').val();
		$j('#ilpDeweightFactorRow').toggle(method !== 'none');
	}
	$j('#ilpDeweightMethod').change(updateDeweightFactorVisibility);
	updateDeweightFactorVisibility();

	$ilpForm.submit(function(e) {
		e.preventDefault();

		var errors = [];
		var values = {};
		var deweightMethod = $j('#ilpDeweightMethod').val();
		clearILPFormErrors();

		// A blank optional field is simply left out of the payload; a blank
		// required one is an error. solveKey marks the solver parameters.
		var nonNegative = function(v) { return v >= 0; };
		var scalarFields = [
			{sel: '.ilpRankWeightInput', required: true, ok: nonNegative, msg: 'Every rank weight must be a number that is at least 0.'},
			{sel: '#ilpInterestWeight', required: true, ok: nonNegative, msg: 'The star weight must be a number that is at least 0.'},
			{sel: '#ilpDeweightFactor', required: deweightMethod !== 'none', ok: function(v) { return v > 0 && v <= 1; }, msg: 'The deweight factor must be a number greater than 0 and at most 1.'},
			{sel: '#ilpMipGap', solveKey: 'MIPGap', ok: isILPNumber, msg: 'The MIP gap must be a number.'},
			{sel: '#ilpMipGapAbs', solveKey: 'MIPGapAbs', ok: isILPNumber, msg: 'The absolute MIP gap must be a number.'},
			{sel: '#ilpTimeLimit', solveKey: 'TimeLimit', ok: function(v) { return v > 0; }, msg: 'The time limit must be a number greater than 0 (leave it blank for unlimited).'},
			{sel: '#ilpThreads', solveKey: 'Threads', ok: function(v) { return v >= 0 && v === Math.floor(v); }, msg: 'The thread count must be a whole number that is at least 0 (leave it blank for the solver default).'},
		];
		$j.each(scalarFields, function(_, field) {
			$j(field.sel).each(function() {
				var $input = $j(this);
				var num = ilpParseNumber($input.val());
				if (isNaN(num)) {
					if (field.required) { addILPError(errors, $input, field.msg); }
				} else if (!field.ok(num)) {
					addILPError(errors, $input, field.msg);
				} else {
					values[field.sel] = (values[field.sel] || []).concat(num);
				}
			});
		});

		var jsonValues = {};
		$j.each([
			['#ilpEmptyStudentSchedulePenalties', 'empty_student_schedule_penalties', validateILPStudentPenalties],
			['#ilpEmptySectionPenaltyPoints', 'empty_section_penalty_points', validateILPSectionPoints],
		], function(_, field) {
			var $jsonField = $j(field[0]);
			var text = $j.trim($jsonField.val());
			if (!text) { return; }
			try {
				jsonValues[field[1]] = JSON.parse(text);
			} catch (err) {
				return addILPError(errors, $jsonField, 'Invalid JSON in ' + field[1] + ': ' + err.message);
			}
			field[2]($jsonField, jsonValues[field[1]], errors);
		});

		if (errors.length > 0) {
			showILPFormErrors(errors);
			return;
		}

		var objective = $j.extend({
			rank_weights: values['.ilpRankWeightInput'] || [],
			interest_weight: values['#ilpInterestWeight'][0],
			check_grade: $j('#ilpCheckGrade').prop('checked'),
			section_len_weight_preset: $j('#ilpSectionLenWeightPreset').val(),
			deweight_by_timeslot: deweightMethod === 'timeslot',
			deweight_by_section: deweightMethod === 'section',
			deweight_factor: (values['#ilpDeweightFactor'] || [])[0],
		}, jsonValues);

		// Seed is always random -- the server fills it in, no field here.
		var solve = {};
		$j.each(scalarFields, function(_, field) {
			if (field.solveKey && values[field.sel]) { solve[field.solveKey] = values[field.sel][0]; }
		});

		var payload = {objective: objective, solve: solve, label: $j('#ilpLabel').val()};
		if ($j('#ilpSolverName').length > 0) {
			payload.solver_name = $j('#ilpSolverName').val();
		}

		var $submitBtn = $j('#ilpSubmit');
		var originalBtnText = $submitBtn.text();
		$submitBtn.prop('disabled', true).text('Submitting… (building model)');

		$j.ajax({
			url: "/manage/" + program_url_base + "/lottery_ilp_submit",
			type: "post",
			data: {'csrfmiddlewaretoken': csrf_token(), 'params': JSON.stringify(payload)},
			success: function(data) {
				var item = data['response'][0];
				if (item.error_msg) {
					alert(item.error_msg);
				} else if (item.run) {
					ilp_expanded_run_ids[item.run.id] = true;
				}
				pollILPStatus();
			},
			error: function() {
				alert('Submitting the ILP lottery run failed. Contact your local webministry for help.');
			},
			complete: function() {
				$submitBtn.prop('disabled', false).text(originalBtnText);
			},
			dataType: 'json'
		});
	});

	pollILPStatus();
	ilp_poll_interval = setInterval(pollILPStatus, 2000);
});
