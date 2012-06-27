Ext.define('LU.view.schedule.Detail', {
    extend: 'Ext.Container',
    xtype: 'scheduleDetail',

    config: {
        layout: 'vbox',
        scrollable: 'vertical',
        items: [
            {
                xtype: 'scheduleInfo'
            },
            {
                xtype: 'schedulePrereqList'
            },
            {
                xtype: 'scheduleTimingList'
            }
        ]
    }
});
