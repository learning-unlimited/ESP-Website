Ext.define('LU.view.student.Schedule', {
    extend: 'Ext.List',
    xtype: 'studentSchedule',

    requires: [
        'Ext.ActionSheet'
    ],

    config: {
        title: 'Schedule',
        cls: 'studentSchedule',
        disableSelection: true,
        grouped: true,
        store: 'Classes',
        itemTpl: Ext.create('Ext.XTemplate',
            '<div class="classes">',
                '<ol>',
                    '<li class="header">',
                        '<div class="code">{code}</div>',
                        '<div class="status {[values.isEnrolled ? "enrolled" : ""]}">',
                            '<tpl if="isEnrolled">Enrolled</tpl>',
                        '</div>',
                    '</li>',
                    '<li class="room">{section_room}</li>',
                '</ol>',
                '<div class="right">',
                    '<div class="stats">',
                        '{section_num_students}/{section_capacity}',
                    '</div>',
                    '<div class="arrow"></div>',
                '</div>',
            '</div>'
        ),
        items: [
            {
                xtype: 'actionsheet',
                hidden: true,
                items: [
                    {
                        text: 'Enroll',
                        itemId: 'action_button',
                        ui: 'confirm'
                    },
                    {
                        text: 'Cancel',
                        itemId: 'cancel_button'
                    }
                ]
            }
        ]
    }
});
