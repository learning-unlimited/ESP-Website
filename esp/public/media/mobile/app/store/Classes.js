Ext.define('LU.store.Classes', {
    extend: 'Ext.data.Store',

    config: {
        autoLoad: false,
        model: 'LU.model.Class',
        sorters: 'title',

        grouper: LU.Util.getTitleGrouper()
    }
});
