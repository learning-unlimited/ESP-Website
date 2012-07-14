Ext.define('LU.store.student.RegisteredSections', {
    extend: 'Ext.data.Store',

    config: {
        autoLoad: false,
        model: 'LU.model.student.RegisteredSection'
    }
});
