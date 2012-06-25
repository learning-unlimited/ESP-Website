Ext.define('LU.model.Class', {
    extend: 'Ext.data.Model',

    config: {

        fields: [
            'category',
            'grade_max',
            'title',
            'prereqs',
            'schedule',
            'class_info',
            'class_size_max',
            'num_questions',
            'class_size_min',
            'grade_min',
            'session_count',
            'num_students',
            'parent_program',
            'teachers',
            'get_sections',
            'section_short_description',
            'section_num_students',
            'section_duration',
            'section_id',
            'section_capacity',
            'section_index',

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
                    var code = record.data.category.symbol + record.data.id
                    if (record.data.section_index > 0) {
                        code += 's' + (record.data.section_index+1);
                    }
                    return code;
                }
            },
            {
                name: 'section_start_time',
                type: 'date',
                convert: function(value, record) {
                    if (value) {
                        var date = value.split(/[\-T:]/);
                        return new Date(date[0], date[1]-1, date[2], date[3]);
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
                        return new Date(date[0], date[1]-1, date[2], date[3]);
                    } else {
                        return new Date();
                    }
                }
            },
        ],

        hasMany: 'LU.model.Timing'
    }
})
