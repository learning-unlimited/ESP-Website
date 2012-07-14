Ext.define('LU.store.onsite.Students', {
    extend: 'Ext.data.Store',

    config: {
        autoLoad: false,
        model: 'LU.model.onsite.Student',
        sorters: 'last_name_upper',

        grouper: LU.Util.getStringGrouper('last_name_upper')
    }
});
