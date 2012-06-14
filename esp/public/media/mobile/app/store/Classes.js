Ext.define('LU.store.Classes', {
    extend: 'Ext.data.Store',

    config: {
        model: 'LU.model.Class',
        sorters: 'title',

        proxy: {
            type: 'ajax',
            url: '/learn/Splash/2012_Summer/catalog_json',

            reader: {
                type: 'json'
            }
        },

        grouper: {
            groupFn: function(record) {
                return record.get('title')[0];
            }
        }
    }
});
