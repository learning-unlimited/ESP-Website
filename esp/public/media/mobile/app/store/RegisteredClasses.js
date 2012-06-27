Ext.define('LU.store.RegisteredClasses', {
    extend: 'Ext.data.Store',

    config: {
        autoLoad: false,
        model: 'LU.model.Class',
        sorters: 'title',

        grouper: LU.Util.getTimeGrouper()
    }
});
