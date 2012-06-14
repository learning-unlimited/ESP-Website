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

        store: 'Classes',
        grouped: true,

        items: [
            { xtype: 'classSortBar' },
            { xtype: 'classSearchBar' }
        ],
        itemTpl: '{title}'
    },
});

