Ext.define('LU.store.RegisteredTimings', {
    extend: 'Ext.data.Store',

    config: {
        autoLoad: false,
        model: 'LU.model.Timing',
        sorters: 'start'
    }
});
