Ext.define('LU.model.Timing', {
    extend: 'Ext.data.Model',

    config: {
        fields: [
            'classes',
            'short_description',
            {
                name: 'start',
                type: 'date',
                convert: function(value, record) {
                    return LU.Util.getDate(value);
                }
            },
            {
                name: 'end',
                type: 'date',
                convert: function(value, record) {
                    return LU.Util.getDate(value);
                }
            }
        ],
    }
});
