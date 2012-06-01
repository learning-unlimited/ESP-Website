Ext.define('LU.view.class.SortBar', {

	extend: 'Ext.Toolbar',
	xtype: 'classSortBar',
	requires: [
	    'Ext.SegmentedButton'
	],

	config: {

		cls: 'sort',
		id: 'sortContainer',
		ui: 'gray',

		items: [
			{
				xtype: 'segmentedbutton',
				id: 'sortBy',
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

