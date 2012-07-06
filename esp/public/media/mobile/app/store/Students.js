Ext.define('LU.store.Students', {
    extend: 'Ext.data.Store',

    config: {
        autoLoad: false,
        model: 'LU.model.Student',
        sorters: 'last_name_upper',

        grouper: LU.Util.getStringGrouper('last_name_upper')
    }
});
