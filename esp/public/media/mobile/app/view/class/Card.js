Ext.define('LU.view.class.Card', {

    extend: 'Ext.NavigationView',
    xtype: 'classContainer',

    config: {
        navigationBar: {
            ui: 'dark',
            docked: 'top',
            items: [
                {
                    xtype: 'button',
                    align: 'right',
                    text: 'Logout'
                }
            ]
        },
        title: 'Classes',
        iconCls: 'note3',

        autoDestroy: false,

        items: [
            {
                xtype: 'classList'
            }
        ]
    }
});

