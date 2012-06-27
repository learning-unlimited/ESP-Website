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
                xtype: 'list',
                cls: 'scheduleList',
                store: 'RegisteredClasses',
                title: 'Registered Classes',
                grouped: true,
                itemTpl: '<div class="classes"><div class="title">{title}</div> <div class="code">{code}</div></div>'
            }
        ]
    }
});
