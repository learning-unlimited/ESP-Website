// ClassSubject model constructor
var ClassSubject = function (data) {
    var self = this;
    self.id          = data.id;
    self.emailcode   = data.emailcode;
    self.title       = data.title;
    self.category    = data.category_id;
    self.class_info  = data.class_info;
    self.grade_min   = data.grade_min;
    self.grade_max   = data.grade_max;
    self.difficulty  = data.difficulty;
    self.prereqs     = data.prereqs;
    self.interested  = ko.observable(false);
    self.interested_saved = ko.observable(false);

    self.fulltitle = data.emailcode + ": " + data.title;
    self.grade_range = data.grade_min + " - " + data.grade_max;

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
        fields.push(self.class_info);
        return fields.join('\0').toLowerCase();
    });

    // click handler for interested star
    self.toggle_interested = function () {
        self.interested(!self.interested());
    }
};

// Section model constructor
var ClassSection = function (data) {
    var self = this;
    self.index = data.index;
    self.times = data.times;
    self.num_students = data.num_students;
    self.capacity = data.capacity;

    self.name = "Section " + data.index;
    self.time = data.times.join(", ");
    self.enrollment = data.num_students + "/" + data.capacity;
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
    self.starredClasses = ko.observableArray([]);
    self.unstarredClasses = ko.observableArray([]);

    // search spinner
    var searchSpinnerOn = function () {
        $j('#search-spinner').spin({
            lines: 8,
            length: 2,
            width: 2,
            radius: 3,
            left: 0
        });
    };
    var searchSpinnerOff = function () {
        $j('#search-spinner').spin(false);
    };

    // search bar
    self.search = ko.observable("");
    self.search.subscribe(searchSpinnerOn);

    self.searchTerm = ko.computed(function () {
        return self.search().toLowerCase();
    }).extend({ throttle: 300 });
    self.searchTerm.subscribe(searchSpinnerOff);

    self.searchPredicate = function (cls) {
        return -1 !== cls.search_key().indexOf(self.searchTerm());
    };

    // show/hide filter options
    self.showFilter = ko.observable(true);
    self.toggleFilter = function () {
        self.showFilter(!self.showFilter());
        // recompute sticky bar height
        var $sticky = $j('#catalog-sticky');
        $sticky.parent().height($sticky.outerHeight());
    };

    // filter options
    self.filterCategory = ko.observableArray();
    self.filterCategory.subscribe(searchSpinnerOn);

    self.filterStarred = ko.observable(catalog_type == 'phase2');
    self.filterStarred.subscribe(searchSpinnerOn);

    self.filterGrade = ko.observable("ALL");
    self.filterGrade.subscribe(searchSpinnerOn);

    self.filterCriteria = ko.computed(function () {
        return {
            'category': self.filterCategory(),
            'starred': self.filterStarred(),
            'grade': self.filterGrade()
        }
    }).extend({ throttle: 100 });
    self.filterCriteria.subscribe(searchSpinnerOff);

    self.filterPredicate = function (cls) {
        var meets_category = false;
        var criteria = self.filterCriteria();
        if (criteria.category.length === 0) {
            meets_category = true;
        }
        else {
            var categories = ko.utils.arrayMap(
                criteria.category,
                function (cat) {
                    return parseInt(cat, 10);
                });
            if (-1 !== categories.indexOf(cls.category)) {
                meets_category = true;
            }
        }

        var meets_grade = false;
        if (catalog_type == 'phase1') {
            if (esp_user.cur_admin === "1") {
                meets_grade = true;
            }
            else {
                var grade = esp_user.cur_grade;
                if (cls.grade_min <= grade &&
                    cls.grade_max >= grade) {
                    meets_grade = true;
                }
            }
        }
        else {
            if (criteria.grade === "ALL") {
                meets_grade = true;
            }
            else {
                var grade = parseInt(criteria.grade, 10);
                if (cls.grade_min <= grade &&
                    cls.grade_max >= grade) {
                    meets_grade = true;
                }
            }
        }

        var meets_starred = true;
        if (criteria.starred) {
            meets_starred = cls.interested();
        }

        return meets_category && meets_grade && meets_starred;
    }

    self.showClass = function (cls) {
        return self.searchPredicate(cls) && self.filterPredicate(cls);
    }

    // priority selection
    var dirty_priorities = false;
    if (catalog_type == 'phase2') {
        self.prioritySelection = [];
        for (var i = 0; i < num_priorities; ++i) {
            self.prioritySelection[i] = ko.observable();
        }
    }

    // loading spinner
    setTimeout(function () {
        $j('#catalog-spinner').spin({
            lines: 10,
            length: 8,
            width: 4,
            radius: 8,
            zIndex: 99
        });
    }, 0);

    var json_views = ['class_subjects/catalog', 'sections/catalog'];
    if (catalog_type == 'phase1') {
        json_views.push('interested_classes');
    }
    else if (catalog_type == 'phase2') {
        json_views.push('interested_classes');
        json_views.push('classes_timeslot/'+timeslot_id);
        json_views.push('lottery_preferences');
    }
    json_fetch(json_views, function (data) {
        // update classes
        for (var key in data.classes) {
            var cls = data.classes[key];
            if (cls.status <= 0) {
                // remove unapproved classes
                delete data.classes[key];
            }
            else if (cls.category_id == open_class_category_id ||
                     cls.category_id == lunch_category_id) {
                // remove lunch and walk-in classes
                delete data.classes[key];
            }
            else if (catalog_type == 'phase2' &&
                     !(key in data.timeslot_subjects)) {
                // remove subjects out of this timeslot
                delete data.classes[key];
            }
            else {
                data.classes[key] = new ClassSubject(cls, self);
                // if marked interested, reflect that.
                if (data.interested_subjects &&
                    key in data.interested_subjects) {
                    data.classes[key].interested(true);
                    data.classes[key].interested_saved(true);
                }
            }
        }
        self.classes(data.classes);
        // update sections
        for (var key in data.sections) {
            var sec = data.sections[key];
            if (sec.status <= 0) {
                // remove un-approved sections
                delete data.sections[key];
            }
            else if (catalog_type == 'phase2' &&
                     !(key in data.timeslot_sections)) {
                // remove sections out of this timeslot
                delete data.sections[key];
            }
            else {
                if (catalog_type == 'phase2') {
                    for (var attr in sec) {
                        if (attr.search('Priority/') == 0) {
                            pri = parseInt(attr.substr(9), 10);
                            self.prioritySelection[pri-1](sec.parent_class);
                        }
                    }
                }
                data.sections[key] = new ClassSection(sec, self);
            }
        }
        self.sections(data.sections);
        // update teachers
        for (var key in data.teachers) {
            data.teachers[key] = new Teacher(data.teachers[key], self);
        }
        self.teachers(data.teachers);
        // update classesArray, starredClasses, unstarredClasses
        var classesQueue = [];
        for (var key in data.classes) {
            var cls = data.classes[key];
            if (cls.interested()) {
                self.starredClasses.push(cls);
            }
            else {
                self.unstarredClasses.push(cls);
            }
            classesQueue.push(cls);
        }
        // sort the classesQueue in an order that is unique to every user
        var sortKey = function (c) {
            var s = esp_user.cur_username + ':' + c.emailcode;
            return CryptoJS.MD5(s).toString();
        }
        classesQueue.sort(function (a, b) {
            var a_key = sortKey(a);
            var b_key = sortKey(b);
            if (a_key < b_key) return -1;
            if (a_key > b_key) return 1;
            return 0;
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
                // set initial values for the phase2 dropdown
                if (catalog_type == 'phase2') {
                    $j('#catalog-sticky .pri-select').change();
                    dirty = false;
                }
            }
        })();
    });

    // get values that need to be updated to the server
    var getDirtyInterested = function () {
        var dirty = false;
        var interested = [];
        var not_interested = [];
        ko.utils.arrayForEach(self.classesArray(), function (cls) {
            if (cls.interested() != cls.interested_saved()) {
                dirty = true;
                if (cls.interested()) {
                    interested.push(cls.id);
                }
                else {
                    not_interested.push(cls.id);
                }
            }
        });
        if (dirty) {
            return {
                interested: interested,
                not_interested: not_interested
            };
        }
        else {
            return false;
        }
    };

    // background updates
    var updateInterested = function () {
        var updates = getDirtyInterested();
        if (updates) {
            // update the server
            var data = {
                csrfmiddlewaretoken: csrf_token(),
                json_data: JSON.stringify(updates)
            }
            var learn_url = program_base_url.replace(/^\/json/, '/learn');
            var url = learn_url + 'mark_classes_interested';
            $j.ajax({
                type: "POST",
                url: url,
                data: data,
                success: function () {
                    // update dirty bits
                    var classes = self.classes();
                    ko.utils.arrayForEach(updates.interested,
                        function (cls_id) {
                            var cls = classes[cls_id];
                            cls.interested_saved(true);
                        });
                    ko.utils.arrayForEach(updates.not_interested,
                        function (cls_id) {
                            var cls = classes[cls_id];
                            cls.interested_saved(false);
                        });
                },
                complete: function () {
                    // if dirty, update again!
                    setTimeout(updateInterested, 1000);
                }
            });
        }
        else {
            // check again in 1 second
            setTimeout(updateInterested, 1000);
        }
    };
    updateInterested();

    // submit handlers for "save and exit" buttons
    var saving = false;
    self.submitInterested = function (form) {
        var $form = $j(form);
        var updates = getDirtyInterested();
        var learn_url = program_base_url.replace(/^\/json/, '/learn');
        if (updates) {
            $form.find("input[name=json_data]").val(
                JSON.stringify(updates));
            $form.attr('action', learn_url + 'mark_classes_interested');
            $form.attr('method', 'post');
        }
        else {
            $form.attr('action', learn_url + 'studentreg');
            $form.attr('method', 'get');
        }
        saving = true;
        return true;
    };
    self.submitPriorities = function(form) {
        var $form = $j(form);
        var learn_url = program_base_url.replace(/^\/json/, '/learn');
        if (dirty) {
            var priorities = {};
            $j('#catalog-sticky .pri-select').each(function() {
                self.prioritySelection[$j(this).data('pri')] = $j(this).val();
            });
            var response = {};
            response[timeslot_id] = self.prioritySelection;
            var json_data = JSON.stringify(response);
            $form.find("input[name=json_data]").val(json_data);
            $form.attr('action', learn_url + 'save_priorities');
            $form.attr('method', 'post');
        }
        else {
            $form.attr('action', learn_url + 'studentreg');
            $form.attr('method', 'get');
        }
        clses = {};
        for (var key in self.prioritySelection) {
            if (self.prioritySelection[key]() in clses) {
                alert('You have listed ' +
                      self.classes()[self.prioritySelection[key]()].fulltitle +
                      ' multiple times. Please fix your preferences.');
                return false;
            }
            clses[self.prioritySelection[key]()] = true;
        }
        
        saving = true;
        return true;
    };

    // warn user if leaving with unsaved changes
    // TODO: figure out how to share this between phases 1 and 2
    if (catalog_type == 'phase1') {
        window.onbeforeunload = function () {
            if (!saving && getDirtyInterested()) {
                return 'Your preferences have not been saved.';
            }
        };
    }
    else if (catalog_type == 'phase2') {
        window.onbeforeunload = function() {
            if (!saving && dirty_priorities) {
                return ('Warning: You have unsaved changes. Please click save' +
                        ' and exit if you wish to preserve your changes.')
            }
        }
    }
};


$j(function () {
    // make sticky bar stick
    $j(function () {
        $j('#catalog-sticky').sticky({
            getWidthFrom: '#content'
        });
    });

    // enable select2
    //$j('#catalog-sticky .pri-select').select2({'width': '20em'});

    // bind viewmodel
    catalog_view_model = new CatalogViewModel();
    ko.applyBindings(catalog_view_model);
});
