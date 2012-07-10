Ext.define('LU.view.student.Detail', {
    extend: 'Ext.Container',
    xtype: 'studentDetail',

    config: {
        activeItem: 0,
        layout: 'card',
        items: [
            {
                xtype: 'studentProfile'
            },
            {
                xtype: 'studentSchedule'
            }
        ]
    }
});
