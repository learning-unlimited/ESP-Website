// helper to update observables of model with values from data if present
var simpleFromJS = function (data, model) {
    for (var key in data) {
        if (ko.isWriteableObservable(model[key])) {
            model[key](data[key]);
        }
    }
};

// ClassSubject model constructor
var ClassSubject = function (data, vm) {
    var self = this;
    self.id          = ko.observable(-1);
    self.emailcode   = ko.observable("");
    self.title       = ko.observable("");
    self.teacher_ids = ko.observableArray();
    self.class_info  = ko.observable("Loading class description...");
    self.grade_min   = ko.observable(-Infinity);
    self.grade_max   = ko.observable(Infinity);
    self.grade_range = ko.observable("Loading...");
    self.difficulty  = ko.observable("Loading...");
    self.prereqs     = ko.observable("Loading...");
    self.section_ids = ko.observableArray();
    self.interested  = ko.observable(false);
    self.dirty       = ko.observable(false);

    self.fulltitle = ko.computed(function () {
	return self.emailcode() + ": " + self.title();
    });

    // teacher objs for the teacher ids
    self.teachers = ko.computed(function () {
        var teachersIndex = vm.teachers();
        var ret = [];
        ko.utils.arrayForEach(self.teacher_ids(), function (teacher_id) {
            var teacher = teachersIndex[teacher_id];
            if (teacher !== undefined) {
                ret.push(teacher);
            }
        });
        return ret;
    });

    // section objs for the section ids
    self.sections = ko.computed(function () {
        var sectionsIndex = vm.sections();
        var ret = [];
        ko.utils.arrayForEach(self.section_ids(), function (section_id) {
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
        fields.push(self.fulltitle());
        ko.utils.arrayForEach(self.teachers(), function (teacher) {
            fields.push(teacher.name());
        });
        fields.push(self.class_info());
        return fields.join('\0').toLowerCase();
    });

    // click handler for interested star
    self.toggle_interested = function () {
        self.interested(!self.interested());
        self.dirty(true);
    }

    // rename attributes: teachers -> teacher_ids, sections -> section_ids
    data.teacher_ids = data.teachers;
    data.section_ids = data.sections;
    delete data.teachers;
    delete data.sections;

    // update model from data
    simpleFromJS(data, self);

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
var ClassSection = function (data, vm) {
    var self = this;
    self.index = ko.observable("");

    self.name = ko.computed(function () {
	return "Section " + self.index();
    });

    simpleFromJS(data, self);
};

// Teacher model constructor
var Teacher = function (data, vm) {
    var self = this;
    self.first_name = ko.observable("");
    self.last_name  = ko.observable("");

    self.name = ko.computed(function () {
        return self.first_name() + " " + self.last_name();
    });

    simpleFromJS(data, self);
};

// Catalog view model constructor
var CatalogViewModel = function () {
    var self = this;
    self.loading = ko.observable(true);
    self.classes = ko.observable({});
    self.sections = ko.observable({});
    self.teachers = ko.observable({});
    self.classesArray = ko.computed(function () {
        var ret = [];
        var classes = self.classes();
        for (var key in classes) {
            ret.push(classes[key]);
        }
        return ret;
    });

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

    json_fetch(['class_subjects', 'sections'], function (data) {
        self.loading(false);
        // update classes
        for (var key in data.classes) {
            data.classes[key] = new ClassSubject(data.classes[key], self);
        }
        self.classes(data.classes);
        // update sections
        for (var key in data.sections) {
            data.sections[key] = new ClassSection(data.sections[key], self);
        }
        self.sections(data.sections);
        // update teachers
        for (var key in data.teachers) {
            data.teachers[key] = new Teacher(data.teachers[key], self);
        }
        self.teachers(data.teachers);
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
    var vm = new CatalogViewModel();
    ko.applyBindings(vm);
});
