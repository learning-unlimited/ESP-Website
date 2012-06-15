Ext.define('LU.controller.Classes', {
    extend: 'Ext.app.Controller',

    config: {
        refs: {
            classList: 'classList',
            sortBy: 'classSortBar segmentedbutton',
            searchField: 'classSearchBar textfield',
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
                show: 'onListShow'
            }
        }
    },

    onSortToggle: function(segBtn, btn) {
        var store = Ext.getStore('Classes');

        if (btn.getText() === 'Title') {
            store.setGrouper({
                groupFn: function(record) {
                    return record.get('title')[0];
                },
                sortProperty: 'title'
            })
        } else if (btn.getText() === 'Difficulty') {
            store.setGrouper({
                groupFn: function(record) {
                    return record.get('hardness_desc');
                },
                sortProperty: 'hardness_rating'     // sorts the grouped headers
            });
            
        } else if (btn.getText() === 'Time') {
            // not implemented yet
        }
        store.sort('title');                        // sorts items within the group
        this.getClassList().setStore(store);
        this.getClassList().deselectAll();
    },

    onListShow: function(list, opts) {
        list.getStore().load();
    },

    onSearch: function(searchField) {
        this.getClassList().deselectAll();

        var store = Ext.getStore('Classes'),
            input = searchField.getValue();

        if (input != '') {
            store.clearFilter(true);
            store.filter('title', input, true);
        } else {
            store.clearFilter();
        }
    },

    onSearchClear: function() {
        Ext.getStore('Classes').clearFilter();
    }
});
