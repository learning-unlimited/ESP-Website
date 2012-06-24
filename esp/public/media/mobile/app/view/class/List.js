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

        cls: 'classList',
        store: 'Classes',
        grouped: true,

        items: [
            { xtype: 'classSortBar' },
            { xtype: 'classSearchBar' }
        ],
        itemTpl: '<div class="classes"><div class="title">{title}</div> <div class="code">{code}</div></div>'
    },
});
