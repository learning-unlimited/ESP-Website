Ext.define('LU.controller.Classes', {
    extend: 'Ext.app.Controller',

    config: {
        refs: {
            classContainer: 'classContainer',
            classList: 'classList',
            timingList: 'timingList',
            classInfo: 'classInfo',
            sortBy: 'classSortBar segmentedbutton',
            searchField: 'classSearchBar searchfield',
            logout: 'classContainer button[text="Logout"]'
        },

        control: {
            sortBy: {
                toggle: 'onSortToggle'
            },
            searchField: {
                action: 'onSearch',
                keyup: 'onSearch',
                clearicontap: 'onSearchClear'
            },
            classContainer: {
                back: 'onBack'
            },
            classList: {
                initialize: 'onListInit',
                show: 'onListShow',
                itemtap: 'onClassTap'
            },
            logout: {
                tap: LU.Util.logout
            }
        }
    },

    search: function(input, store) {
        store.clearFilter();
        if (input != '') {
            store.filter('title', input, true);
        }
    },

    onSortToggle: function(segBtn, btn) {
        var store = Ext.getStore('Classes');

        if (btn.getText() === 'Title') {
            store.setGrouper(LU.Util.getStringGrouper('title_upper'));
        } else if (btn.getText() === 'Difficulty') {
            store.setGrouper(LU.Util.getDifficultyGrouper());
        } else if (btn.getText() === 'Time') {
            store.setGrouper(LU.Util.getTimeGrouper());
        }
        store.sort('title_upper');                    // sorts items within the group
        this.getClassList().setStore(store);
        this.getClassList().deselectAll();
    },

    onBack: function(container, opts) {
        if (container.up('onsite')) {
            container.getNavigationBar().hide();
        }
    },

    onListInit: function(list, opts) {
        list.getStore().clearFilter();
        list.getStore().setGrouper(LU.Util.getStringGrouper('title_upper'));
        list.getStore().sort('title_upper');
    },

    onListShow: function(list, opts) {
        // saves the search result when going between views
        this.search(this.getSearchField().getValue(), list.getStore());

        // show Logout button
        this.getLogout().show();
    },

    onClassTap: function(list, index, target, record, event, opts) {
        if (!this.classDetail) {
            this.classDetail = Ext.widget('classDetail');
        }
        this.classDetail.config.title = record.get('title');
        this.getClassContainer().getNavigationBar().show();
        this.getClassContainer().push(this.classDetail);
        this.getClassInfo().setRecord(record);

        // hide Logout button
        this.getLogout().hide();

        var classStore = Ext.getStore('Classes'),
            classId = record.get('id');

        // apply filter for Prereq list
        classStore.filter('id', classId);

        // use foreign key to get timings
        this.getTimingList().setStore(classStore.first().timings());
    },

    onSearch: function(searchField) {
        this.getClassList().deselectAll();
        this.search(searchField.getValue(), Ext.getStore('Classes'));
    },

    onSearchClear: function() {
        Ext.getStore('Classes').clearFilter();
    }
});
