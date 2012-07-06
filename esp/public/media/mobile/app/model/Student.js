Ext.define('LU.model.Student', {
    extend: 'Ext.data.Model',

    config: {
        fields: [
            'id',
            'first_name',
            'last_name',
            'username',
            'email',

            {
                name: 'last_name_upper',
                type: 'string',
                convert: function(value, record) {
                    return record.data.last_name.toUpperCase();
                }
            }
        ]
    }
});
