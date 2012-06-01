Ext.define('LU.view.student.Main', {
    extend: 'Ext.tab.Panel',
    xtype: 'mainStudent',
    
    config: {
        tabBarPosition: 'bottom',
        items: [
            {
                xclass: 'LU.view.class.Card'
            },
            {
                title: 'Favorites',
                iconCls: 'star',
                html: 'Favorites Screen'
            }
        ]
    }
});

