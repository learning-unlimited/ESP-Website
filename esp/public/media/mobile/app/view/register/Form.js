Ext.define('LU.view.register.Form', {
    extend: 'LU.view.base.Panel',
    xtype: 'registerForm',

    requires: [
        'Ext.field.Email'
    ],

    config: {
        cls: 'registerForm',
        iconCls: 'compose',
        title: 'Register',
        layout: {
            type: 'vbox',
            pack: 'center'
        },
        items: [
            {
                xtype: 'toolbar',
                docked: 'top',
                title: 'Register'
            },
            {
                xtype: 'fieldset',
                cls: 'mainForm',
                items: [
                    {
                        xtype: 'textfield',
                        itemId: 'first_name_field',
                        name: 'first_name',
                        label: 'First Name',
                        labelCls: 'label'
                    },
                    {
                        xtype: 'textfield',
                        itemId: 'last_name_field',
                        name: 'last_name',
                        label: 'Last Name',
                        labelCls: 'label'
                    },
                    {
                        xtype: 'emailfield',
                        itemId: 'email_field',
                        name: 'email',
                        label: 'Email',
                        labelCls: 'label'
                    },
                    {
                        xtype: 'numberfield',
                        itemId: 'grade_field',
                        name: 'grade',
                        minValue: 7,
                        maxValue: 12,
                        label: 'Grade',
                        labelCls: 'label'
                    }
                ]
            },
            {
                xtype: 'button',
                text: 'Submit',
                ui: 'confirm'
            }
        ]
    }
});
