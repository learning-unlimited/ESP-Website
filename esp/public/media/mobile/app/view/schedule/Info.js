Ext.define('LU.view.schedule.Info', {
    extend: 'Ext.Component',
    xtype: 'scheduleInfo',

    config: {
        cls: 'scheduleInfo',
        tpl: Ext.create('Ext.XTemplate',
            '<div class="title">{title} <div class="code">{code}</div></div>',
            '<div class="description">{class_info}</div>'
        )
   }
});
