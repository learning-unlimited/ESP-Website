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
            sectionStore = Ext.getStore('Sections');

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

                        var timeItem = sectionItem.get_meeting_times[0];
                        classModel.set('id', parseInt('' + classItem.id + sectionItem.id));
                        classModel.set('section_short_description', timeItem.short_description);
                        classModel.set('section_start_time', timeItem.start);
                        classModel.set('section_end_time', timeItem.end);
                        classModel.set('section_id', sectionItem.id);
                        classModel.set('section_capacity', sectionItem.capacity);
                        classModel.set('section_num_students', sectionItem.num_students);
                        classModel.set('section_duration', sectionItem.duration);
                        classStore.add(classModel);
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
