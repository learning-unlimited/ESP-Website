Ext.define('LU.controller.Classes', {
    extend: 'Ext.app.Controller',

    config: {
        refs: {
            classContainer: 'classContainer',
            classList: 'classList',
            timingList: 'timingList',
            classInfo: 'classInfo',
            sortBy: 'classSortBar segmentedbutton',
            searchField: 'classSearchBar textfield',
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
            classList: {
                initialize: 'onListInit',
                show: 'onListShow',
                itemtap: 'onClassTap'
            },
            logout: {
                tap: 'onLogout'
            }
        },

        titleGrouper: {
            groupFn: function(record) {
                return record.get('title')[0];
            },
            sortProperty: 'title'               // sorts the grouped headers
        },

        difficultyGrouper: {
            groupFn: function(record) {
                return record.get('hardness_desc');
            },
            sortProperty: 'hardness_rating'
        },

        timeGrouper: {
            groupFn: function(record) {
                // formatting syntax: http://docs.sencha.com/ext-js/4-0/#!/api/Ext.Date
                return Ext.Date.format(record.get('section_start_time'), 'g:i A');
            },
            sortProperty: 'section_start_time'
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
            store.setGrouper(this.getTitleGrouper());
        } else if (btn.getText() === 'Difficulty') {
            store.setGrouper(this.getDifficultyGrouper());
        } else if (btn.getText() === 'Time') {
            store.setGrouper(this.getTimeGrouper());
        }
        store.sort('title');                    // sorts items within the group
        this.getClassList().setStore(store);
        this.getClassList().deselectAll();
    },

    onListInit: function(list, opts) {
        list.getStore().clearFilter();
        list.getStore().setGrouper(this.getTitleGrouper());
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
        this.getClassContainer().push(this.classDetail);
        this.getClassInfo().setRecord(record);

        // hide Logout button
        this.getLogout().hide();

        // apply filter for Prereq list
        Ext.getStore('Classes').filter('id', record.get('id'));

        // apply filter for Timing list
        var store = Ext.getStore('Timings');
        store.clearFilter();
        store.filter('class_id', record.get('id'));
    },

    onSearch: function(searchField) {
        this.getClassList().deselectAll();
        this.search(searchField.getValue(), Ext.getStore('Classes'));
    },

    onSearchClear: function() {
        Ext.getStore('Classes').clearFilter();
    },

    onLogout: function() {
        Ext.Ajax.request({
            url: '/myesp/ajax_signout/',
            success: function(result) {
                Ext.Viewport.getActiveItem().destroy();
                Ext.Viewport.setActiveItem(Ext.widget('main'));
            },
            failure: function(result) {
                Ext.Msg.alert('Logout Error', 'An unknown error has occurred. You may wish to try logging out later.');
            }
        });
    }
});
