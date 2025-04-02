(function () {
	// Set up AudioContext. If none, then quit.
	var AC = window.AudioContext ||
		window.webkitAudioContext ||
		window.mozAudioContext ||
		window.oAudioContext ||
		window.msAudioContext;
	if (!AC) { return; }
	var ac = null; // create during event handler in order to start unmuted
	// Library of scales
	var scales = [
		[1, 9/8, 5/4, 4/3, 3/2, 5/3, 15/8], // Pythagorean-ish major scale
		[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(function (x) { return Math.pow(2, x/12); }), // Chromatic
		[1, 9/8, 5/4, 3/2, 5/3], // Pentatonic Major
		[1, 9/8, 5/4, 3/2, 16/9], // Arpeggio
		[1, 6/5, 3/2, 5/3, 15/8], // Another pretty arpeggio
	];
	var makeNote = function (buffer) {
		// Make a playable (by calling) note out of a buffer
		return function () {
			var s = ac.createBufferSource();
			s.buffer = buffer;
			s.connect(ac.destination);
			if (s.noteOn) { s.noteOn(ac.currentTime); }
			else { s.start(ac.currentTime); }
		};
	};
	var registered_listeners = [];
	var makeMusical = function (container) {
		// Piano-keys-ize all of the nav tabs in the given container.
		// First, find the set of keys
		var items = container.querySelectorAll('li:not(.hidden)');
		// Choose a random scale
		var scale = scales[Math.floor((scales.length - 0.00001) * Math.random())];
		// Render notes
		var base_freq = 440;
		var notes = Array.prototype.map.call(items, function (target, i) {
			// Create a new sample
			var buf = ac.createBuffer(1, ac.sampleRate * 4, ac.sampleRate);
			var data = buf.getChannelData(0);
			// Choose frequency, decay, and amplitude
			var index = items.length - i - 1;
			var rate = base_freq * scale[index % scale.length] * Math.pow(2, Math.floor(index/scale.length + 0.00001)) * 2 * Math.PI / ac.sampleRate;
			var decay = Math.pow(0.5, 1/(0.2 * ac.sampleRate));
			var y = 0.1 * Math.pow(0.5, index / scale.length) + 0.1 * i / items.length;
			var x = 0;
			// Calculate waveform
			var dx = Math.cos(rate) * decay;
			var dy = Math.sin(rate) * decay;
			for (var j = 0; j < data.length; j++) {
				data[j] = x * dx - y * dy;
				y = x * dy + y * dx;
				x = data[j];
				data[j] *= Math.min(j / (0.01 * ac.sampleRate), (data.length - j) / data.length);
			}
			return makeNote(buf);
		});
		// Remove any pre-existing scale
		for (var i = 0; i < registered_listeners.length; ++i) {
			registered_listeners[i][0].removeEventListener('mouseenter', registered_listeners[i][1]);
		}
		registered_listeners.length = 0;
		// Attach notes to tabs
		for (var i = 0; i < items.length; i++) {
			items[i].addEventListener('mouseenter', notes[i]);
			registered_listeners.push([items[i], notes[i]]);
		}
		return notes;
	};
	var codeListener = (function () {
		var last_keys = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
		var i = 0;
		var checkSequence = function (seq) {
			var j = i;
			while (seq.length > 0) {
				j = (j + last_keys.length - 1) % last_keys.length;
				if (seq.pop() != last_keys[j]) { return false; }
			}
			return true;
		};
		return function (e) {
			var keycode = e.type == "keydown" ? e.which : 13;
			if (keycode == 13) {
				if (checkSequence([88, 89, 90, 90, 89]) || // Colossal Cave Adventure
					checkSequence([73, 68, 68, 81, 68]) || // Doom
					checkSequence([38, 38, 40, 40, 37, 39, 37, 39, 66, 65]) // Konami
				) {
					if (ac === null) { ac = new AC(); }
					makeMusical(document.getElementById('menu'));
				}
			}
			last_keys[i] = keycode;
			i = (i + 1) % last_keys.length;
		};
	})();
	document.addEventListener('keydown', codeListener);
})();
