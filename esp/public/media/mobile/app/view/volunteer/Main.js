Ext.define('LU.view.volunteer.Main', {
    extend: 'Ext.tab.Panel',
    xtype: 'mainVolunteer',
    
    config: {
        tabBarPosition: 'bottom',
        items: [
            {
                title: 'Search',
                iconCls: 'search',
                html: 'Search Screen'
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

