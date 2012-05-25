Ext.define("LU.view.Main", {
    extend: 'Ext.Container',
    
    requires: [
        'LU.view.login.LoggedOut'
    ],
    
    config: {
        layout: 'fit',
        cls: 'loggedOut',
        
        items: [
            {
                xtype: 'container',
                layout: {
                    type: 'vbox',
                    align: 'center'
                },
                cls: 'loginScreen',
                items: [
                    {
                        xtype: 'loggedOut'
                    }
                ]
            }
        ]
    }
});

