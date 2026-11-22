// The print panel (program/modules/dayof/print_panel.html). The location chosen is remembered in this browser (''
// for the Default location, as the old receipt print control stored it), so pages and tabs opened afterwards start
// on it; tabs already open keep what they show.
//
// After it sends jobs, a page hands their ids to espPrintPanel.watch(panel, ids) (or, after a form posts and comes
// back, the panel is given them: {% print_panel watch=... %}), and the panel shows how each is getting on (waiting,
// the printer's trouble, printed, failed) until all are done.
(function () {
    var KEY = 'esp_print_location';
    var POLL_MS = 3000;
    var WATCH_FOR_MS = 20 * 60 * 1000;      // then stop asking (the Printer Setup page still shows the job)
    var SHOW_JOBS = 5;                      // the latest (e.g. the help desk sends one schedule after another)

    function stored() {
        try { return window.localStorage.getItem(KEY); } catch (e) { return null; }
    }
    function store(value) {
        try { window.localStorage.setItem(KEY, value); } catch (e) {}
    }

    function init(panel) {
        if (panel.getAttribute('data-ready')) { return; }
        panel.setAttribute('data-ready', '1');
        var data = JSON.parse(panel.querySelector('.print-panel-data').textContent);
        var select = panel.querySelector('.print-panel-location');
        var byId = {}, defaultId = null;
        data.locations.forEach(function (l) {
            byId[String(l.id)] = l;
            if (l.is_default) { defaultId = String(l.id); }
        });

        function restore() {
            var saved = stored();
            if (saved === null) { return; }
            var id = saved === '' ? defaultId : saved;
            if (id !== null && byId[id]) { select.value = id; }
        }

        function show() {
            var l = byId[select.value], defaults = data.defaults || {};
            var status = panel.querySelector('.print-panel-status small');
            var network = l && l.mode === 'network' && l.connected;
            status.className = '';
            status.textContent = '';
            if (l && !l.connected) {
                var d = byId[defaultId];
                status.className = d && d.connected && !l.is_default ? 'muted' : 'text-error';
                status.textContent = l.is_default || !(d && d.connected) ?
                    'No printer currently connected for this location.' :
                    'No printer currently connected for this location, so Default prints it.';
            } else if (l && l.trouble) {
                status.className = 'text-error';
                status.textContent = 'Not printing right now: ' + l.trouble;
            }
            var fieldset = panel.querySelector('.print-panel-settings');
            if (!fieldset) { return; }     // (a panel without printer settings)
            fieldset.hidden = !network;
            panel.querySelector('.print-panel-no-settings').hidden = !l || network || !l.connected;
            fieldset.querySelectorAll('[data-setting]').forEach(function (group) {
                var key = group.getAttribute('data-setting'), field = group.querySelector('select');
                var values = network ? (l.capabilities[key] || []) : [];
                var own = network ? l.settings[key] : '';
                field.innerHTML = '';
                var first = document.createElement('option');
                first.value = '';
                first.textContent = own ? 'location setting (' + own + ')' : 'printer default';
                field.appendChild(first);
                values.forEach(function (v) {
                    var option = document.createElement('option');
                    option.value = v;
                    option.textContent = v;
                    field.appendChild(option);
                });
                if (defaults[key] && values.indexOf(defaults[key]) >= 0 && defaults[key] !== own) {
                    field.value = defaults[key];
                }
                group.hidden = !values.length;
            });
        }

        if (data.watch && data.watch.length) { watch(panel, data.watch); }

        select.addEventListener('change', function () {
            var l = byId[select.value];
            store(l && l.is_default ? '' : select.value);
            show();
        });
        restore();
        show();
    }

    // Shows the jobs' progress in the panel, asking the server every POLL_MS until each is done
    function watch(panel, ids) {
        var state = panel.espPrintWatch;
        if (!state) {
            var data = JSON.parse(panel.querySelector('.print-panel-data').textContent);
            state = panel.espPrintWatch = {url: data.status_url, jobs: {}, order: [], timer: null, until: 0};
        }
        (ids || []).forEach(function (id) {
            id = String(id);
            if (!(id in state.jobs)) {
                state.jobs[id] = {text: 'Job #' + id + ': sent.', level: 'muted', done: false};
                state.order.push(id);
            }
        });
        state.until = Date.now() + WATCH_FOR_MS;
        render(panel, state);
        if (!state.timer) { poll(panel, state); }
    }

    function render(panel, state) {
        var box = panel.querySelector('.print-panel-jobs');
        if (!box) { return; }
        box.innerHTML = '';
        state.order.slice(-SHOW_JOBS).forEach(function (id) {
            var job = state.jobs[id], line = document.createElement('div'), text = document.createElement('small');
            line.className = {error: 'text-error', success: 'text-success'}[job.level] || 'muted';
            text.textContent = job.text;
            line.appendChild(text);
            box.appendChild(line);
        });
    }

    function poll(panel, state) {
        var waiting = state.order.slice(-SHOW_JOBS).filter(function (id) { return !state.jobs[id].done; });
        if (!waiting.length || Date.now() > state.until) { state.timer = null; return; }
        state.timer = window.setTimeout(function () {
            fetch(state.url + '?jobs=' + waiting.join(','), {credentials: 'same-origin'}).then(function (r) {
                if (!r.ok) { throw new Error('HTTP ' + r.status); }
                return r.json();
            }).then(function (body) {
                (body.jobs || []).forEach(function (job) {
                    if (String(job.id) in state.jobs) { state.jobs[String(job.id)] = job; }
                });
                render(panel, state);
            }).catch(function () {
                // (logged out, or the server is restarting: try again next time)
            }).then(function () { poll(panel, state); });
        }, POLL_MS);
    }

    function initAll() {
        document.querySelectorAll('.print-panel').forEach(init);
    }

    if (!window.espPrintPanel) {
        window.espPrintPanel = {
            init: initAll,
            watch: watch,
            // The panel's fields as an object (for a script that posts them itself)
            values: function (panel) {
                var out = {};
                panel.querySelectorAll('select[name], input[name]').forEach(function (field) {
                    if (!field.closest('[hidden]')) { out[field.name] = field.value; }
                });
                return out;
            }
        };
    }
    initAll();
})();
