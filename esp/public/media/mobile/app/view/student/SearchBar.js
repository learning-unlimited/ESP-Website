Ext.define('LU.view.student.SearchBar', {

    extend: 'Ext.form.Panel',
    xtype: 'studentSearchBar',

    requires: [
        'Ext.field.Search'
    ],

    config: {

        scrollable: false, // Override the form panel
        cls: 'search',

        items: [
            {
                xtype: 'searchfield',
                labelWidth: 0,
                inputCls: 'searchField',
                placeHolder: 'Search for username, name, email'
            }
        ]
	}
});
