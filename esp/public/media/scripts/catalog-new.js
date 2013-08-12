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
};

$j(function () {
    var vm = new CatalogViewModel();
    ko.applyBindings(vm);
});
