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
    self.dirty       = ko.observable(false);

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
        self.dirty(true);
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

    self.filterGrade = ko.observable("ALL");
    self.filterGrade.subscribe(searchSpinnerOn);

    self.filterCriteria = ko.computed(function () {
        return {
            'category': self.filterCategory(),
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

        return meets_category && meets_grade;
    }

    self.showClass = function (cls) {
        return self.searchPredicate(cls) && self.filterPredicate(cls);
    }

    // priority selection
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
	json_views.push('interested_classes/'+timeslot_id);
	json_views.push('lottery_preferences');
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
            if (data.sections[key].status <= 0) {
		// remove un-approved sections
		delete data.sections[key];
            }
	    else if (catalog_type == 'phase2' &&
		     !(key in data.interested_sections)) {
		// remove non-interested sections
		delete data.sections[key];
	    }
            else {
		if (catalog_type == 'phase2') {
		    for (var attr in data.sections[key]) {
			if (attr.search('Priority/') == 0) {
			    pri = parseInt(attr.substr(9), 10);
			    self.prioritySelection[pri-1](data.sections[key].parent_class);
			}
		    }
		}
                data.sections[key] = new ClassSection(data.sections[key], self);
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

    var getDirtyInterested = function () {
        var dirty = [];
        ko.utils.arrayForEach(self.classesArray(), function (cls) {
            if (cls.dirty()) {
                dirty.push(cls);
            }
        })
        return dirty;
    };
    var updateInterested = function () {
        var dirty = getDirtyInterested();
        ko.utils.arrayForEach(dirty, function (cls) {
            cls.dirty(false);
        });
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
