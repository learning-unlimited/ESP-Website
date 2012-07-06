Ext.define('LU.store.Classes', {
    extend: 'Ext.data.Store',

    config: {
        autoLoad: false,
        model: 'LU.model.Class',
        sorters: 'title_upper',

        grouper: LU.Util.getStringGrouper('title_upper')
    }
});
