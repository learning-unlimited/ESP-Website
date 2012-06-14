Ext.define('LU.model.Class', {
    extend: 'Ext.data.Model',

    config: {
        idProperty: 'id',

        fields: [
            'category',
            'grade_max',
            'title',
            'prereqs',
            'schedule',
            'class_info',
            'anchor',
            'class_size_max',
            'num_questions',
            'class_size_min',
            'grade_min',
            'session_count',
            'num_students',
            'parent_program',
            'id',
            'teachers',

            {
                name: 'hardness_rating',
                type: 'int',
                convert: function(value, record) {
                    return value.length;
                }
            },
            {
                name: 'hardness_desc',
                type: 'string',
                convert: function(value, record) {
                    switch(record.data.hardness_rating) {
                        case 1:
                            return 'Easy';
                        case 2:
                            return 'Moderate';
                        case 3:
                            return 'Difficult';
                        case 4:
                            return 'Very Difficult';
                    }
                }
            }
        ],

        proxy: {
            type: 'ajax',
            url: '/learn/Splash/2012_Summer/catalog_json',

            reader: {
                type: 'json'
            }
        }
    }
})
