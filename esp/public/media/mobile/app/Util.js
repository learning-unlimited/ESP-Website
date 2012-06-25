Ext.define('LU.Util', {

    singleton: true,

    constructor: function(config) {
        this.initConfig(config);
        this.callParent([config]);
    },

    getProgram: function() {
        return Ext.getStore('User').first().getProgram();
    },

    getCatalogUrl: function() {
        return '/learn/' + this.getProgram().get('baseUrl') + '/catalog_json';
    },

    getProgramTitle: function() {
        return this.getProgram().get('title');
    },

    getClasses: function(callback) {

        var url = this.getCatalogUrl(),
            classStore = Ext.getStore('Classes'),
            timeStore = Ext.getStore('Timings');

        // clears any previous existing models
        classStore.removeAll();
        timeStore.removeAll();

        Ext.Ajax.request({
            url: url,
            success: function(result) {

                var data = Ext.JSON.decode(result.responseText);

                // flattens the data received from server
                // i.e. each section will have its individual record
                Ext.Array.each(data, function(classItem, classIndex, classList) {

                    var sections = classItem.get_sections;
                    Ext.Array.each(sections, function(sectionItem, sectionIndex, sectionList) {

                        // section_index is used to derive the class code
                        var classModel = Ext.create('LU.model.Class', Ext.apply(classItem, {section_index: sectionIndex}));

                        classModel.set('id', parseInt('' + classItem.id + sectionItem.id));
                        classModel.set('section_id', sectionItem.id);
                        classModel.set('section_capacity', sectionItem.capacity);
                        classModel.set('section_num_students', sectionItem.num_students);
                        classModel.set('section_duration', sectionItem.duration);
                        classStore.add(classModel);

                        // maps the meeting times to each record
                        var timings = sectionItem.get_meeting_times;
                        Ext.Array.each(timings, function(timeItem, timeIndex, timeList) {

                            // note: currently we only use the first meeting time to perform sorting
                            if (timeIndex == 0) {
                                classModel.set('section_short_description', timeItem.short_description);
                                classModel.set('section_start_time', timeItem.start);
                                classModel.set('section_end_time', timeItem.end);
                            }
                            var timeModel = Ext.create('LU.model.Timing', timeItem);
                            timeModel.set('id', parseInt('' + classModel.get('id') + timeItem.id));
                            timeModel.setClass(classModel.get('id'));
                            timeStore.add(timeModel);
                        });
                    });
                });
                callback();
            },
            failure: function(result) {
                callback(result);
            }
        });
    }
});
