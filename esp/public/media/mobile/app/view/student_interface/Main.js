Ext.define('LU.view.student_interface.Main', {
    extend: 'Ext.tab.Panel',
    xtype: 'student',

    config: {
        tabBarPosition: 'bottom',
        items: [
            {
                xclass: 'LU.view.class.Card'
            },
            {
                xclass: 'LU.view.schedule.Card'
            }
        ]
    }
});

