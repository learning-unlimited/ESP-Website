Ext.define('LU.store.Timings', {
    extend: 'Ext.data.Store',

    config: {
        autoLoad: false,
        model: 'LU.model.Timing',
        sorters: 'start'
    }
});
