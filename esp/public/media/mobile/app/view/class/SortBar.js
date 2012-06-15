Ext.define('LU.view.class.SortBar', {

	extend: 'Ext.Toolbar',
	xtype: 'classSortBar',
	requires: [
	    'Ext.SegmentedButton'
	],

	config: {

		cls: 'sort',
		ui: 'gray',

		items: [
			{
				xtype: 'segmentedbutton',
				flex: 1,

				layout: {
					pack: 'center'
				},

				defaults: {
		    		xtype: 'button',
		    		flex: 1
				},

				items: [
		    		{ text: 'Title', pressed: true },
		    		{ text: 'Time' },
		    		{ text: 'Difficulty' }
				]
			}
		]
	}
});

