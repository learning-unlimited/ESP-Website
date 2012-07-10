Ext.define('LU.view.student.Profile', {
    extend: 'Ext.form.Panel',
    xtype: 'studentProfile',

    requires: [
        'Ext.form.FieldSet',
        'Ext.field.Number'
    ],

    config: {
        cls: 'studentProfile',
        title: 'Profile',
        layout: {
            type: 'vbox'
        },
        items: [
            {
                xtype: 'panel',
                cls: 'user-panel',
                layout: {
                    type: 'hbox',
                    align: 'end',
                    pack: 'start'
                },
                items: [
                    {
                        xtype: 'component',
                        itemId: 'namecard',
                        tpl: Ext.create('Ext.XTemplate',
                            '<div class="namecard">',
                                '<div class="name">{first_name} {last_name}</div>',
                                '<div class="account">{username} ({id})</div>',
                            '</div>'
                        )
                    },
                    {
                        xtype: 'button',
                        cls: 'check-in-btn',
                        ui: 'confirm-small',
                        text: 'Check-in'
                    }
                ]
            },
            {
                xtype: 'component',
                cls: 'separator line'
            },
            {
                xtype: 'fieldset',
                cls: 'contact',
                title: 'Contact Info',
                items: [
                    {
                        xtype: 'textfield',
                        itemId: 'email_field',
                        name: 'email',
                        label: 'Email',
                        labelCls: 'label',
                        readOnly: true
                    },
                    {
                        xtype: 'textareafield',
                        itemId: 'phone_field',
                        name: 'phone',
                        label: 'Phone',
                        labelCls: 'label',
                        readOnly: true
                    },
                    {
                        xtype: 'textareafield',
                        itemId: 'address_field',
                        height: '4em',
                        name: 'address',
                        label: 'Address',
                        labelCls: 'label',
                        readOnly: true
                    }
                ]
            },
            {
                xtype: 'fieldset',
                cls: 'student',
                title: 'Student Info',
                items: [
                    {
                        xtype: 'textfield',
                        itemId: 'school_field',
                        name: 'school',
                        label: 'School',
                        labelCls: 'label',
                        readOnly: true
                    },
                    {
                        xtype: 'numberfield',
                        itemId: 'grade_field',
                        name: 'grade',
                        minValue: 6,
                        maxValue: 12,
                        label: 'Grade',
                        labelCls: 'label'
                    },
                    {
                        xtype: 'textfield',
                        itemId: 'grad_yr_field',
                        name: 'graduation_year',
                        label: 'Graduation Year',
                        labelCls: 'label',
                        readOnly: true,
                        style: {
                            'text-overflow': 'clip',
                            'word-space': 'normal'
                        }
                    },
                    {
                        xtype: 'textfield',
                        itemId: 'dob_field',
                        name: 'dob',
                        label: 'Date of Birth',
                        labelCls: 'label',
                        readOnly: true
                    }
                ]
            }
        ]
    }
});
