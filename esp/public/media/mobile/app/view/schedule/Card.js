Ext.define('LU.view.schedule.Card', {
    extend: 'Ext.NavigationView',
    xtype: 'scheduleContainer',

    config: {
        navigationBar: {
            ui: 'dark',
            docked: 'top'
        },
        title: 'Schedule',
        iconCls: 'time',

        autoDestroy: false,

        items: [
            {
                xtype: 'scheduleList'
            }
        ]
    }
});
