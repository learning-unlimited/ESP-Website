Ext.define('LU.view.class.List', {

    extend: 'Ext.List',
    xtype: 'classList',
    requires: [
        'Ext.form.Panel',
        'Ext.TitleBar',

        'LU.view.class.SortBar',
        'LU.view.class.SearchBar'
    ],

    config: {

        items: [
            { xtype: 'classSortBar' },
            { xtype: 'classSearchBar' }
        ]
    }
});

