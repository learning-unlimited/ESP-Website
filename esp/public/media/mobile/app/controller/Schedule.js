Ext.define('LU.controller.Schedule', {
    extend: 'Ext.app.Controller',

    config: {
        refs: {
            scheduleContainer: 'scheduleContainer',
            scheduleList: 'scheduleContainer list',
            timingList: 'timingList',
            scheduleInfo: 'scheduleInfo'
        },

        control: {
            scheduleList: {
                show: 'onListShow',
                itemtap: 'onClassTap'
            }
        }
    },

    onListShow: function(list, opts) {
        Ext.getStore('RegisteredClasses').clearFilter();
    },

    onClassTap: function(list, index, target, record, event, opts) {
        if (!this.scheduleDetail) {
            this.scheduleDetail = Ext.widget('scheduleDetail');
        }
        this.scheduleDetail.config.title = record.get('title');
        this.getScheduleContainer().push(this.scheduleDetail);
        this.getScheduleInfo().setRecord(record);

        // apply filter for Prereq list
        Ext.getStore('RegisteredClasses').filter('id', record.get('id'));

        // apply filter for Timing list
        store = Ext.getStore('RegisteredTimings');
        store.clearFilter();
        store.filter('class_id', record.get('id'));
    }
});
