Ext.define('LU.view.login.Form', {
    extend: 'LU.view.base.Panel',
    xtype: 'loginForm',

    requires: [
        'Ext.Spacer',
        'Ext.field.Text',
        'Ext.field.Password'
    ],

    config: {
        scrollable: false,
        cls: 'login',
        items: [
            {
                xtype: 'component',
                cls: 'logo',
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
                name: 'password',
                autoComplete: false,
                autoCorrect: false
            }
        ]
    }
});

