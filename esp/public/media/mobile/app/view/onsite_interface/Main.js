Ext.define('LU.view.onsite_interface.Main', {
    extend: 'Ext.tab.Panel',
    xtype: 'onsite',

    config: {
        tabBarPosition: 'bottom',
        items: [
            {
                xclass: 'LU.view.student.Card'
            },
            {
                title: 'Register',
                iconCls: 'compose',
                html: 'Register Screen'
            },
            {
                title: 'Schedule',
                iconCls: 'time',
                html: 'Schedule Screen'
            }
        ]
    }
});

