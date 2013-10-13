// helper to update observables of model with values from data if present
var simpleFromJS = function (data, model) {
    for (var key in data) {
        if (ko.isWriteableObservable(model[key])) {
            model[key](data[key]);
        }
    }
};

// ClassSubject model constructor
var ClassSubject = function (data) {
    var self = this;
    self.id          = data.id;
    self.emailcode   = data.emailcode;
    self.title       = data.title;
    self.class_info  = ko.observable("Loading class description...");
    self.grade_min   = data.grade_min;
    self.grade_max   = data.grade_max;
    self.grade_range = ko.observable("Loading...");
    self.difficulty  = ko.observable("Loading...");
    self.prereqs     = ko.observable("Loading...");
    self.interested  = ko.observable(false);
    self.dirty       = ko.observable(false);

    self.fulltitle = data.emailcode + ": " + data.title;

    // teacher objs for the teacher ids
    self.teachers = ko.computed(function () {
        var teachersIndex = catalog_view_model.teachers();
        var ret = [];
        ko.utils.arrayForEach(data.teachers, function (teacher_id) {
            var teacher = teachersIndex[teacher_id];
            if (teacher !== undefined) {
                ret.push(teacher);
            }
        });
        return ret;
    });

    // section objs for the section ids
    self.sections = ko.computed(function () {
        var sectionsIndex = catalog_view_model.sections();
        var ret = [];
        ko.utils.arrayForEach(data.sections, function (section_id) {
            var section = sectionsIndex[section_id];
            if (section !== undefined) {
                ret.push(section)
            }
        });
        return ret;
    });

    // key for the search box
    self.search_key = ko.computed(function () {
        var fields = [];
        fields.push(self.fulltitle);
        ko.utils.arrayForEach(self.teachers(), function (teacher) {
            fields.push(teacher.name);
        });
        fields.push(self.class_info());
        return fields.join('\0').toLowerCase();
    });

    // click handler for interested star
    self.toggle_interested = function () {
        self.interested(!self.interested());
        self.dirty(true);
    }

    // get detailed class info
    // temporary hack until class_subjects view can return this info
    var id = data.id;
    json_fetch(["class_info?class_id=" + id], function (data) {
        data = data.classes[id];
        data.section_ids = data.sections;
        delete data.sections;
        simpleFromJS(data, self);
    });
};

// Section model constructor
var ClassSection = function (data) {
    var self = this;
    self.index = data.index;
    self.name = "Section " + data.index;
};

// Teacher model constructor
var Teacher = function (data) {
    var self = this;
    self.first_name = data.first_name;
    self.last_name  = data.last_name;

    self.name = data.first_name + " " + data.last_name;
};

// Catalog view model constructor
var CatalogViewModel = function () {
    var self = this;
    self.loading = ko.observable(true);
    self.classes = ko.observable({});
    self.sections = ko.observable({});
    self.teachers = ko.observable({});
    self.classesArray = ko.observableArray([]);

    // search bar
    self.search = ko.observable("");
    self.search.subscribe(function () {
        $j('#search-spinner').spin({
            lines: 8,
            length: 2,
            width: 2,
            radius: 3,
            left: 0
        });
    });
    self.searchTerm = ko.computed(function () {
        return self.search().toLowerCase();
    }).extend({ throttle: 300 });
    self.searchTerm.subscribe(function () {
        $j('#search-spinner').spin(false);
    });

    self.searchPredicate = function (cls) {
        return -1 !== cls.search_key().indexOf(self.searchTerm());
    };

    self.showFilter = ko.observable(true);
    self.toggleFilter = function () {
        self.showFilter(!self.showFilter());
        // recompute sticky bar height
        var $sticky = $j('#catalog-sticky');
        $sticky.parent().height($sticky.outerHeight());
    };

    // loading spinner
    setTimeout(function () {
        $j('#catalog-spinner').spin({
            lines: 10,
            length: 8,
            width: 4,
            radius: 8,
        });
    }, 0);

    var json_views = ['class_subjects', 'sections'];
    if (catalog_type == 'phase1' || catalog_type == 'phase2') {
	json_views.push('interested_classes');
    }
    json_fetch(json_views, function (data) {
        // update classes
        for (var key in data.classes) {
            if (data.classes[key].status <= 0) {
                // remove unapproved classes
                delete data.classes[key];
            }
	    else if (catalog_type == 'phase2' &&
		     !(key in data.interested_subjects)) {
		// remove non-interested subjects
		delete data.classes[key];
	    }
            else {
                data.classes[key] = new ClassSubject(data.classes[key], self);
                // if marked interested, reflect that.
                if (key in data.interested_subjects) {
                    data.classes[key].interested(true);
                }
            }
        }
        self.classes(data.classes);
        // update sections
        for (var key in data.sections) {
            if (data.sections[key].status > 0) {
                data.sections[key] = new ClassSection(data.sections[key], self);
            }
	    else if (catalog_type == 'phase2' &&
		     !(key in data.interested_sections)) {
		// remove non-interested sections
		delete data.sections[key];
	    }
            else {
                // remove unapproved sections
                delete data.sections[key];
            }
        }
        self.sections(data.sections);
        // update teachers
        for (var key in data.teachers) {
            data.teachers[key] = new Teacher(data.teachers[key], self);
        }
        self.teachers(data.teachers);
        // update classesArray
        var classesQueue = [];
        for (var key in data.classes) {
            classesQueue.push(data.classes[key]);
        }
        // sort the classesQueue in an order that is unique to every user
        hashCode = function(s) {
            var hash = 0;
            if (s.length == 0) return hash;
            for (i = 0; i < s.length; i++) {
                char = s.charCodeAt(i);
                hash = ((hash<<5)-hash)+char;
                hash = hash & hash; // convert to 32bit integer
            }
            return hash;
        }
        classesQueue.sort(function (a, b) {
            var a_key = esp_user.cur_username + a.emailcode;
            var b_key = esp_user.cur_username + b.emailcode;
            return hashCode(a_key) - hashCode(b_key);
        });
        // add classes to the UI not-all-at-once so as to not hang the browser
        (function dequeueClass () {
            if (classesQueue.length > 0) {
                // add a chunk of classes
                var t = Date.now();
                self.classesArray.push.apply(self.classesArray,
                                             classesQueue.splice(-20).reverse());
                var dt = Date.now() - t;
                // wait awhile before adding more
                setTimeout(dequeueClass, dt);
            }
            else {
                // done loading all classes; remove "loading" message
                self.loading(false);
                $j('#catalog-spinner').spin(false);
            }
        })();
    });

    var getDirtyInterested = function () {
        var dirty = [];
        ko.utils.arrayForEach(self.classesArray(), function (cls) {
            if (cls.dirty()) {
                dirty.push(cls);
                cls.dirty(false);
            }
        })
        return dirty;
    };
    var updateInterested = function () {
        var dirty = getDirtyInterested();
        if (dirty.length > 0) {
            // update the server
            var interested = [];
            var not_interested = [];
            ko.utils.arrayForEach(dirty, function (cls) {
                if (cls.interested()) {
                    interested.push(cls.id);
                }
                else {
                    not_interested.push(cls.id);
                }
            });
            var data = {
                csrfmiddlewaretoken: csrf_token(),
                json_data: JSON.stringify({
                    interested: interested,
                    not_interested: not_interested
                })
            }
            var learn_url = program_base_url.replace(/^\/json/, '/learn');
            var url = learn_url + 'mark_classes_interested';
            $j.ajax({
                type: "POST",
                url: url,
                data: data,
                error: function () {
                    // update failed, re-queue
                    ko.utils.arrayForEach(self.classesArray(), function (cls) {
                        cls.dirty(true);
                    });
                },
                complete: updateInterested // if dirty, update again!
            });
        }
        else {
            // check again in 1 second
            setTimeout(updateInterested, 1000);
        }
    };
    updateInterested();
    window.onbeforeunload = function () {
        if (getDirtyInterested().length > 0) {
            return 'Your preferences have not been saved.';
        }
    };
};

$j(function () {
    // make sticky bar stick
    $j(function () {
        $j('#catalog-sticky').sticky({
            getWidthFrom: '#content'
        });
    });

    // bind viewmodel
    catalog_view_model = new CatalogViewModel();
    ko.applyBindings(catalog_view_model);
});
