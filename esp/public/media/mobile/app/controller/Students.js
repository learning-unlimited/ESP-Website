Ext.define('LU.controller.Students', {
    extend: 'Ext.app.Controller',

    config: {
        // variables to remember who last accessed the views
        accessedDetail: 0,
        accessedSchedule: 0,

        refs: {
            studentContainer: 'studentContainer',
            navigationBarTitle: 'studentContainer title',
            studentList: 'studentList',
            studentProfile: 'studentProfile',
            studentSchedule: 'studentSchedule',
            studentInfo: 'studentProfile #namecard',
            searchField: 'studentSearchBar searchfield',
            phoneField: 'studentProfile textareafield[name="phone"]',
            gradeField: 'studentProfile #grade_field',
            actionSheet: 'studentSchedule actionsheet',
            segmentedButton: 'studentContainer segmentedbutton',
            checkInButton: 'studentProfile #checkin_button',
            changeGradeButton: 'studentProfile #change_grade_button',
            actionButton: 'studentSchedule actionsheet #action_button',
            cancelButton: 'studentSchedule actionsheet #cancel_button',
            logout: 'studentContainer button[text="Logout"]'
        },

        control: {
            studentList: {
                show: 'onListShow',
                itemtap: 'onStudentTap'
            },
            studentSchedule: {
                select: function() { return false; },
                itemtap: 'onScheduleTap'
            },
            searchField: {
                action: 'onSearch',
                keyup: 'onSearch',
                clearicontap: 'onSearchClear'
            },
            segmentedButton: {
                toggle: 'onToggle'
            },
            checkInButton: {
                tap: 'onCheckIn'
            },
            changeGradeButton: {
                tap: 'onChangeGrade'
            },
            actionButton: {
                tap: 'onAction'
            },
            cancelButton: {
                tap: 'onCancel'
            },
            logout: {
                tap: LU.Util.logout
            }
        }
    },

    search: function(input, store) {
        store.clearFilter();
        if (input != '') {
            var regex = new RegExp('^' + input, 'i');
            store.filter([
                {
                    filterFn: function(record) {
                        return record.get('last_name').match(regex) ||
                               record.get('first_name').match(regex) ||
                               record.get('username').match(regex) ||
                               record.get('email').match(regex);
                    }
                }
            ]);
        }
    },

    checkIn: function(button, isCheckedIn) {
        button.setDisabled(isCheckedIn);

        if (isCheckedIn) {
            button.setText('Checked-in');
            button.setStyle({
                'background-image': '-webkit-linear-gradient(#3E5702,#507003 10%,#628904 65%,#648C04)',
                'color': '#eee'
            });
        } else {
            button.setText('Check-in');
            button.setStyle({
                'background-image': '-webkit-linear-gradient(#C2FA3B,#85BB05 2%,#547503)',
                'color': '#fff'
            });
        }
    },

    clearFieldValues: function() {
        Ext.Array.each(this.getStudentProfile().query('textfield,textareafield,numberfield'), function(field) {
            field.setValue('');
        });
    },

    setFieldValue: function(itemId, property) {

        var object = this.getStudentProfile().down('#'+itemId);

        if (itemId == 'checkin_button') {
            this.checkIn(object, this.profile.get(property));
            return;
        } else {
            object.setValue(this.profile.get(property));
        }

        if (itemId == 'phone_field') {
            if (this.profile.get(property).indexOf('\n') > -1) {
                // adjust to double row
                this.getPhoneField().setHeight('4em');
            } else {
                this.getPhoneField().setHeight('2em');
            }
        }
    },

    resetStudentDetail: function() {
        this.segmentedButton.setPressedButtons(this.segmentedButton.getItems().first());
        this.studentDetail.setActiveItem(0);
        this.studentDetail.getActiveItem().getScrollable().getScroller().scrollTo(0,0);
    },

    goToStudentDetail: function() {
        this.getStudentContainer().push(this.studentDetail);

        // setup the navigation bar with segmented buttons
        var navbar = this.getStudentContainer().getNavigationBar();
        if (!this.segmentedButton) {
            this.segmentedButton = new Ext.SegmentedButton({
                centered: true,
                align: 'center',
                allowDepress: false,
                items: [
                    {
                        iconCls: 'user',
                        iconMask: true,
                        itemId: 'profile-tab',
                        pressed: true
                    },
                    {
                        iconCls: 'note2',
                        itemId: 'schedule-tab',
                        iconMask: true
                    }
                ]
            });
        } else {
            this.segmentedButton.show();
        }
        navbar.rightBox.hide();
        navbar.spacer.hide();
        navbar.leftBox.setWidth('100%');
        navbar.add(this.segmentedButton);
    },

    loadProfile: function(id) {
        var profileStore = Ext.getStore('StudentProfiles'),
            profileUrl = LU.Util.getStudentProfileUrl(id);

        Ext.Viewport.setMasked({ xtype: 'loadmask' });
        profileStore.setProxy({
            type: 'ajax',
            url: profileUrl
        });
        profileStore.removeAll();
        profileStore.load({
            callback: function(records, operation, success) {
                this.profile = records[0];
                this.setFieldValue('email_field', 'email');
                this.setFieldValue('phone_field', 'phone');
                this.setFieldValue('address_field', 'address');
                this.setFieldValue('school_field', 'school');
                this.setFieldValue('grad_yr_field', 'graduation_year');
                this.setFieldValue('grade_field', 'grade');
                this.setFieldValue('dob_field', 'dob');
                this.setFieldValue('checkin_button', 'checkin_status');
                Ext.Viewport.setMasked(false);
                this.goToStudentDetail();
                this.resetStudentDetail();
            },
            scope: this
        });
    },

    showScheduleList: function() {
        var studentId = this.profile.get('id'),
            container = this.studentDetail;

        Ext.Viewport.setMasked({ xtype: 'loadmask' });
        LU.Util.getRegisteredClasses(function(result) {
            if (!result) {
                var classStore = Ext.getStore('Classes');
                classStore.setGrouper(LU.Util.getTimeGrouper());
                classStore.sort('code');
                container.setActiveItem(1);
            } else {
                Ext.Msg.alert('Network Error', 'We are experiencing problems fetching the data from server. You may wish to try reloading again.');
            }
            Ext.Viewport.setMasked(false);
        }, studentId);
    },

    onListShow: function(list, opts) {
        // show Logout button
        this.getLogout().show();
        this.getNavigationBarTitle().show();

        var navbar = this.getStudentContainer().getNavigationBar();
        navbar.rightBox.show();
        navbar.spacer.show();
        navbar.leftBox.setWidth(null);
        if (this.segmentedButton) {
            this.segmentedButton.hide();
        }
    },

    onStudentTap: function(list, index, target, record, event, opts) {
        var studentId = record.get('id');
        if (!this.studentDetail) {
            this.studentDetail = Ext.widget('studentDetail');
        }
        this.getStudentInfo().setData(record.data);

        // retrieves the previously accessed view from memory
        if (this.getAccessedDetail() == studentId) {
            this.goToStudentDetail();
        } else {
            this.loadProfile(studentId);
        }

        // hide Logout button
        this.getLogout().hide();

        this.setAccessedDetail(studentId);
    },

    toggleActionSheetButton: function(state) {
        if (state === 'E') {
            this.getActionButton().setText('Enroll');
            this.getActionButton().setUi('confirm');
        } else  if (state === 'W') {
            this.getActionButton().setText('Withdraw');
            this.getActionButton().setUi('decline');
        }
    },

    checkConflict: function(section) {
        var timeStore = section.timings(),
            classStore = Ext.getStore('Classes'),
            enrolledClasses = [], conflictClasses = [];

        // gets currently enrolled classes
        classStore.each(function(record) {
            if (record.get('isEnrolled')) {
                enrolledClasses.push(record.get('id'));
            }
        });

        // compares the list of enrolled classes and obtains the classes that conflict
        timeStore.each(function(record) {
            conflictClasses = Ext.Array.merge(Ext.Array.intersect(enrolledClasses, record.get('classes')), conflictClasses);
        })

        if (conflictClasses.length > 0) {
            return conflictClasses;
        }
        return false;
    },

    getSectionCodes: function(list) {
        var codes = [],
            classStore = Ext.getStore('Classes');
        Ext.Array.each(list, function(item, index, listItself) {
            codes.push(classStore.findRecord('id', item).get('code'));
        });
        return codes;
    },

    updateClassRecord: function() {
        var c = this.classRecord;
        c.set('isEnrolled', !c.get('isEnrolled'));

        var num = parseInt(c.get('section_num_students'));
        if (c.get('isEnrolled')) {
            num++;
        } else {
            num--;
        }
        c.set('section_num_students', num);

        Ext.getStore('Classes').sync();
    },

    onScheduleTap: function(list, index, target, record, event, opts) {
        if (!record.get('isEnrolled')) {
            if (record.get('section_num_students') >= record.get('section_capacity')) {
                Ext.Msg.alert('Full Capacity', 'This section is currently full or oversubscribed.');
                return;
            } else if (this.profile.get('grade') < record.get('grade_min') || this.profile.get('grade') > record.get('grade_max')) {
                Ext.Msg.alert('Grade Prerequisite', 'This class is for grades ' + record.get('grade_min') + '-' + record.get('grade_max'));
                return;
            } else {
                var conflictClasses = this.checkConflict(record);
                if (conflictClasses) {
                    Ext.Msg.alert('Class Conflict', 'This class conflicts with ' + this.getSectionCodes(conflictClasses).join(', ') + '.');
                    return;
                }
            }
        }
        this.classRecord = record;
        this.target = target;
        this.toggleActionSheetButton(record.get('isEnrolled') ? 'W' : 'E');
        this.getActionSheet().show();
    },

    onSearch: function(searchField) {
        this.search(searchField.getValue(), Ext.getStore('Students'));
    },

    onSearchClear: function() {
        Ext.getStore('Students').clearFilter();
    },

    onToggle: function(segmentedButton, button, isPressed, opts) {
        if (button.getItemId() == 'profile-tab') {
            this.studentDetail.setActiveItem(0);
        } else if (button.getItemId() == 'schedule-tab') {
            var studentId = this.profile.get('id');
            if (this.getAccessedSchedule() == studentId) {
                this.studentDetail.setActiveItem(1);
            } else {
                this.showScheduleList();
                this.setAccessedSchedule(studentId);
            }
        }
    },

    onCheckIn: function(button, event, opts) {

        // show checked in button first
        this.checkIn(button, true);

        LU.Util.ajaxPost({
            url: LU.Util.getRapidCheckInUrl(),
            params: {
                'user': this.profile.get('id')
            },
            success: function(result) {
                // do nothing
            },
            failure: function(result) {
                this.checkIn(button, false);
                Ext.Msg.alert('Network Error', 'Try checking-in again later.');
            },
            scope: this
        });
    },

    onChangeGrade: function() {
        Ext.Viewport.setMasked({ xtype: 'loadmask' });

        var new_grade = parseInt(this.getGradeField().getValue());
        LU.Util.ajaxPost({
            url: LU.Util.getChangeGradeUrl(),
            params: {
                'user': this.profile.get('id'),
                'grade': new_grade
            },
            success: function(result) {
                var grad_yr_field = this.getStudentProfile().down('#grad_yr_field'),
                    old_grade = parseInt(this.profile.get('grade')),
                    old_grad_yr = parseInt(grad_yr_field.getValue()),
                    new_grad_yr = old_grad_yr + old_grade - new_grade;

                // update the graduation year based on new grade
                grad_yr_field.setValue(new_grad_yr.toString().replace(',', ''));

                // update local storage
                this.profile.set('grade', new_grade);

                Ext.Viewport.setMasked(false);
            },
            failure: function(result) {
                // restores the old value
                this.setFieldValue('grade_field', 'grade');
                Ext.Viewport.setMasked(false);
            },
            scope: this
        });
    },

    onAction: function(button, event, opts) {

        // update status and stats
        this.updateClassRecord();

        var classStore = Ext.getStore('Classes');
        classStore.sync();

        // find the enrolled sections
        var enrolledSections = [];
        classStore.each(function(record) {
            if (record.get('isEnrolled')) {
                enrolledSections.push(record.get('section_id'));
            }
        }, this);

        Ext.Ajax.request({
            url: LU.Util.getUpdateScheduleUrl(this.profile.get('id'), enrolledSections.toString(), false),
            success: function(result) {
                // do nothing
            },
            failure: function(result) {
                Ext.Msg.alert('Network Error', 'We are experiencing problems fetching the data from server. You may wish to try reloading again.');

                // revert back the changes made previously
                this.updateClassRecord();
            },
            scope: this
        });
        this.getActionSheet().hide();
    },

    onCancel: function() {
        this.getActionSheet().hide();
    }
});
