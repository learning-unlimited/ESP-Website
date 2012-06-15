Ext.define('LU.view.TitleBar', {
    extend: 'Ext.TitleBar',
    xtype: 'titleBar',

    config: {
        docked: 'top',
        title: 'Welcome!',
        items: [
            {
                align: 'right',
                text: 'Logout'
            }
        ]
    }
});
