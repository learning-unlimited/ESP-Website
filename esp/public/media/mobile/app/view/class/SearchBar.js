Ext.define('LU.view.class.SearchBar', {

	extend: 'Ext.form.Panel',
	xtype: 'classSearchBar',
	requires: [
	    'Ext.field.Text'
	],

	config: {

    	scrollable: false, // Override the form panel
        cls: 'search',

        items: [
        	{
        		xtype: 'textfield',
        		clearIcon: true,
        		labelWidth: 0,
		        inputCls: 'searchField',
                placeHolder: 'Search for class'
        	}
        ]
	}
});

