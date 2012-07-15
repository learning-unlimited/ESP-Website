Ext.define('LU.view.student.Schedule', {
    extend: 'Ext.List',
    xtype: 'studentSchedule',

    config: {
        title: 'Schedule',
        cls: 'studentSchedule',
        grouped: true,
        store: 'Classes',
        itemTpl: Ext.create('Ext.XTemplate',
            '<div class="classes">',
                '<ol>',
                    '<li class="header">',
                        '<div class="code">{code}</div>',
                        '<tpl if="isEnrolled">',
                            '<div class="status">Enrolled</div>',
                        '</tpl>',
                    '</li>',
                    '<li class="room">{section_room}</li>',
                '</ol>',
                '<div class="stats">',
                    '{section_num_students}/{section_capacity}',
                '</div>',
            '</div>'
        )
    }
});
