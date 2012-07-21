Ext.define('LU.view.schedule.List', {
    extend: 'Ext.List',
    xtype: 'scheduleList',

    config: {
        cls: 'scheduleList',
        disableSelection: true,
        store: 'RegisteredClasses',
        title: 'Registered Classes',
        grouped: true,
        itemTpl: '<div class="classes"><div class="title">{title}</div> <div class="code">{code}</div></div>'
    }
});
