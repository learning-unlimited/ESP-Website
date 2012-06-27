Ext.define('LU.store.RegisteredSections', {
    extend: 'Ext.data.Store',

    config: {
        autoLoad: false,
        model: 'LU.model.RegisteredSection'
    }
});
