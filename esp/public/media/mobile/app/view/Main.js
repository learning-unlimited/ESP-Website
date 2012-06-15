Ext.define("LU.view.Main", {
    extend: 'Ext.Container',
    xtype: 'main',
    
    requires: [
        'LU.view.login.Form'
    ],
    
    config: {
        layout: 'fit',
        cls: 'loginForm',
        
        items: [
            {
                xtype: 'container',
                layout: {
                    type: 'vbox',
                    align: 'center'
                },
                cls: 'loginContainer',
                items: [
                    {
                        xtype: 'loginForm'
                    }
                ]
            }
        ]
    }
});

