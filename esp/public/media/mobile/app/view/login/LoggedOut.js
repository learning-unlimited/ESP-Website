Ext.define('LU.view.login.LoggedOut', {
    extend: 'LU.view.Panel',
    xtype: 'loggedOut',
    
    requires: [
        'Ext.field.Password'
    ],
    
    config: {
        scrollable: false,
        items: [
            {
                xtype: 'component',
                id: 'logo',
                html: '<div>ESP</div>',        // TODO: replace with image
            },
            {
                xtype: 'spacer',
                cls: 'separator'
            },
            {
                xtype: 'textfield',
                clearIcon: true,
                labelWidth: 0,
                placeHolder: 'Username',
                cls: ['field', 'first'],
                id: 'username',
                name: 'username',
                autoComplete: false,
                autoCorrect: false
            },
            {
                xtype: 'passwordfield',
                clearIcon: true,
                labelWidth: 0,
                placeHolder: 'Password',
                cls: ['field', 'last'],
                id: 'password',
                name: 'password',
                autoComplete: false,
                autoCorrect: false
            }
        ]
    }
});

