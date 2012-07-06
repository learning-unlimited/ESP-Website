Ext.define('LU.view.student.SearchBar', {

    extend: 'Ext.form.Panel',
    xtype: 'studentSearchBar',

    config: {

        scrollable: false, // Override the form panel
        cls: 'search',

        items: [
            {
                xtype: 'textfield',
                clearIcon: true,
                labelWidth: 0,
                inputCls: 'searchField',
                placeHolder: 'Search for username, name, email'
            }
        ]
	}
});
