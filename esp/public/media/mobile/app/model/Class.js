Ext.define('LU.model.Class', {
    extend: 'Ext.data.Model',

    config: {

        fields: [
            'category',
            'parent_program',
            'title',
            'prereqs',
            'schedule',
            'grade_max',
            'grade_min',
            'class_info',
            'class_size_max',
            'class_size_min',
            'num_questions',
            'num_students',
            'teachers',
            'get_sections',
            'session_count',
            'section_short_description',
            'section_num_students',
            'section_duration',
            'section_id',
            'section_capacity',
            'section_index',
            'section_room',
            'isEnrolled',

            {
                name: 'title_upper',
                type: 'string',
                convert: function(value, record) {
                    return record.data.title.toUpperCase();
                }
            },
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
            },
            {
                name: 'code',
                type: 'string',
                convert: function(value, record) {
                    return record.data.category.symbol + record.data.id + 's' + (record.data.section_index+1);
                }
            },
            {
                name: 'section_start_time',
                type: 'date',
                convert: function(value, record) {
                    if (value) {
                        var date = value.split(/[\-T:]/);
                        return new Date(date[0], date[1]-1, date[2], date[3], date[4]);
                    } else {
                        return new Date();
                    }
                }
            },
            {
                name: 'section_end_time',
                type: 'date',
                convert: function(value, record) {
                    if (value) {
                        var date = value.split(/[\-T:]/);
                        return new Date(date[0], date[1]-1, date[2], date[3], date[4]);
                    } else {
                        return new Date();
                    }
                }
            },
        ],

        hasMany: 'LU.model.Timing'
    }
})
