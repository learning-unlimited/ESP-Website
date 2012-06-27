Ext.define('LU.view.schedule.Prereq', {
    extend: 'Ext.List',
    xtype: 'schedulePrereqList',

    config: {
        disableSelection: true,
        scrollable: false,
        store: 'RegisteredClasses',

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
