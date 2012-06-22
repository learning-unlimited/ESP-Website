Ext.define('LU.store.Programs', {
    extend: 'Ext.data.Store',

    config: {
        model: 'LU.model.Program',

        proxy: {
            type: 'ajax',
            url: '/myesp/program',

            reader: {
                type: 'json'
            }
        },
    }
});