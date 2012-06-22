Ext.define('LU.store.Classes', {
    extend: 'Ext.data.Store',

    config: {
        autoLoad: false,
        model: 'LU.model.Class',
        sorters: 'title',

        proxy: {
            type: 'ajax',
            reader: {
                type: 'json'
            }
        },

        grouper: {
            groupFn: function(record) {
                return record.get('title')[0];
            }
        },

        listeners: {
            beforeload: function(store, operation, opts) {
                store.getProxy().setUrl(LU.Util.getCatalogUrl());
            }
        }
    }
});
