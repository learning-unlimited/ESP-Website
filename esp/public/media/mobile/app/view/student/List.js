Ext.define('LU.view.student.List', {

    extend: 'Ext.List',
    xtype: 'studentList',

    requires: [
        'LU.view.student.SearchBar'
    ],

    config: {

        cls: 'studentList',
        store: 'Students',
        title: 'Welcome!',
        grouped: true,
        indexBar: true,
        disableSelection: true,

        items: [
            {
                xtype: 'studentSearchBar'
            }
        ],
        itemTpl: Ext.create('Ext.XTemplate',
            '<div class="students">',
                '<ol>',
                    '<li class="name"><span class="bold">{last_name}</span>,&nbsp;{first_name}</li>',
                    '<li class="email">{email}</li>',
                '</ol>',
                '<div class="username">{username}</div>',
            '</div>'
        )
    }
});
