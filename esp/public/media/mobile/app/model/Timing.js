Ext.define('LU.model.Timing', {
    extend: 'Ext.data.Model',

    config: {
        fields: [
            'short_description',
            {
                name: 'start',
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
                name: 'end',
                type: 'date',
                convert: function(value, record) {
                    if (value) {
                        var date = value.split(/[\-T:]/);
                        return new Date(date[0], date[1]-1, date[2], date[3]);
                    } else {
                        return new Date();
                    }
                }
            }
        ],

        belongsTo: 'LU.model.Class'
    }
});
