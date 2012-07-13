Ext.define('LU.view.class.SearchBar', {

	extend: 'Ext.form.Panel',
	xtype: 'classSearchBar',
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
                placeHolder: 'Search for class'
            }
        ]
	}
});

