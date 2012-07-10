Ext.define('LU.model.StudentProfile', {
    extend: 'Ext.data.Model',

    config: {
        fields: [
            'name',
            'email',
            'phone_day',
            'phone_cell',
            'address',
            'school',
            'graduation_year',
            'grade',
            'dob',

            {
                name: 'phone',
                type: 'string',
                convert: function(value, record) {
                    var day, cell;
                    if (record.data.phone_day.length > 0) {
                        day = record.data.phone_day + ' (Day)';
                    }
                    if (record.data.phone_cell.length > 0) {
                        cell = record.data.phone_cell + ' (Cell)';
                    }

                    if (day && cell) {
                        return day + '\n' + cell;
                    } else if (day) {
                        return day;
                    } else if (cell) {
                        return cell;
                    }
                    return '';
                }
            }
        ]
    }
});
