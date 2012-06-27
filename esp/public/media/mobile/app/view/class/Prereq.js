Ext.define('LU.view.class.Prereq', {
    extend: 'Ext.List',
    xtype: 'classPrereqList',

    config: {
        disableSelection: true,
        scrollable: false,
        store: 'Classes',

        items: [
            {
                xtype: 'listitemheader',
                html: 'Prerequisites'
            }
        ],

        itemTpl: Ext.create('Ext.XTemplate',
            '{[ values.prereqs.length > 0 ? values.prereqs : "None" ]}'
        )
    }
});
