/**
 * Dialog box to set the comment for class.
 *
 * @param el: The element to use for dialog
 * @param sections: The sections object of the scheduler
 */
function SectionCommentDialog(el, sections) {
    this.el = el;
    this.modal = bootstrap.Modal.getOrCreateInstance(el[0]);
    el.find('#commentDialog-save').on("click", function() {
        this.doSetComment();
        this.modal.hide();
    }.bind(this));
    el[0].addEventListener('hidden.bs.modal', function() {
        this.el.find('form')[0].reset();
    }.bind(this));
    this.sections = sections;

    /**
     * Show the dialog for the given section.
     */
    this.show = function(section) {
        this.el.data('section', section.id);
        this.el.find('#commentDialog-comment').val(section.schedulingComment);
        if(section.schedulingLocked) {
            this.el.find('#commentDialog-lock').prop("checked", true);
        }
        this.modal.show();
    }.bind(this);

    this.doSetComment = function() {
        var section = this.sections.sections_data[this.el.data('section')];
        this.sections.setComment(section,
                                 this.el.find('#commentDialog-comment').val(),
                                 this.el.find('#commentDialog-lock').prop("checked"));
    }.bind(this);
}
