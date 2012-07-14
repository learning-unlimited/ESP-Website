Ext.define('LU.store.student.RegisteredTimings', {
    extend: 'Ext.data.Store',

    config: {
        autoLoad: false,
        model: 'LU.model.Timing',
        sorters: 'start'
    }
});
