Ext.define('LU.model.onsite.StudentProfile', {
    extend: 'Ext.data.Model',

    config: {
        fields: [
            // user info
            {
                name: 'id',
                mapping: 'user.id'
            },
            {
                name: 'name',
                mapping: 'user.name'
            },
            {
                name: 'grade',
                mapping: 'user.grade'
            },
            {
                name: 'checkin_status',
                mapping: 'user.checkin_status',
                type: 'boolean'
            },

            // contact info
            {
                name: 'email',
                mapping: 'contact.email'
            },
            {
                name: 'phone_day',
                mapping: 'contact.phone_day'
            },
            {
                name: 'phone_cell',
                mapping: 'contact.phone_cell'
            },
            {
                name: 'address',
                mapping: 'contact.address'
            },

            // student info
            {
                name: 'school',
                mapping: 'student.school'
            },
            {
                name: 'graduation_year',
                mapping: 'student.graduation_year'
            },
            {
                name: 'dob',
                mapping: 'student.dob'
            },

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
