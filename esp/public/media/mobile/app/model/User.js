Ext.define('LU.model.User', {
    extend: 'Ext.data.Model',

    requires: [ 'Ext.data.proxy.LocalStorage' ],

    config: {
        idProperty: 'id',

        fields: [
            'id', 'role', 'program_id'
        ],

        hasOne: 'LU.model.Program'
    }
});
