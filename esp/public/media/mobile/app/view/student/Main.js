Ext.define('LU.view.student.Main', {
    extend: 'Ext.tab.Panel',
    xtype: 'mainStudent',
    
    config: {
        tabBarPosition: 'bottom',
        items: [
            {
                title: 'Classes',
                iconCls: 'time',
                html: 'Classes Screen'
            },
            {
                title: 'Favorites',
                iconCls: 'star',
                html: 'Favorites Screen'
            }
        ]
    }
});

