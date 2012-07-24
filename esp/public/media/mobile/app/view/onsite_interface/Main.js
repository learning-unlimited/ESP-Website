Ext.define('LU.view.onsite_interface.Main', {
    extend: 'Ext.tab.Panel',
    xtype: 'onsite',

    config: {
        tabBarPosition: 'bottom',
        items: [
            { xtype: 'studentContainer' },
            { xtype: 'registerForm' },
            {
                title: 'Schedule',
                iconCls: 'time',
                html: 'Schedule Screen'
            }
        ]
    }
});

