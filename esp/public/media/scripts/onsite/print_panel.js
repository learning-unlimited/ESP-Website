// The print panel (program/modules/dayof/print_panel.html). The location chosen is remembered in this browser (''
// for the Default location, as the old receipt print control stored it), so pages and tabs opened afterwards start
// on it; tabs already open keep what they show.
(function () {
    var KEY = 'esp_print_location';

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

        select.addEventListener('change', function () {
            var l = byId[select.value];
            store(l && l.is_default ? '' : select.value);
            show();
        });
        restore();
        show();
    }

    function initAll() {
        document.querySelectorAll('.print-panel').forEach(init);
    }

    if (!window.espPrintPanel) {
        window.espPrintPanel = {
            init: initAll,
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
