Ext.define('LU.controller.Schedule', {
    extend: 'Ext.app.Controller',

    config: {
        refs: {
            scheduleContainer: 'scheduleContainer',
            scheduleList: 'scheduleContainer list',
            timingList: 'scheduleTimingList',
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
        var registeredClassStore = Ext.getStore('RegisteredClasses'),
            registeredClassId = record.get('id');
        registeredClassStore.filter('id', registeredClassId);

        // use foreign key to get timings
        this.getTimingList().setStore(registeredClassStore.first().timings());
    }
});
