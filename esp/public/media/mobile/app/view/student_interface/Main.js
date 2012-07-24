Ext.define('LU.view.student_interface.Main', {
    extend: 'Ext.tab.Panel',
    xtype: 'student',

    config: {
        tabBarPosition: 'bottom',
        items: [
            { xtype: 'classContainer' },
            { xtype: 'scheduleContainer' }
        ]
    }
});

