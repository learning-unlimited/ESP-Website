/**
 * The panel that shows error and log messages to the user.
 *
 * @param el: The element to render into the panel
 * @param initialMessage: The message to go initially on the panel
 */
function MessagePanel(el, initialMessage) {
    this.el = el;

    /**
     * Initialize the pannel with the initial message
     */
    this.init = function() {
        if(initialMessage) {
            this.addMessage(initialMessage);
        }
    };

    /**
     * Append a line to the message div in the form of a <p>.
     *
     * @param msg: The message to add
     */
    this.addMessage = function(msg) {
        this.el.append( "<p>" + msg + "</p>");
        // some browsers need delay before scrollHeight is updated
        setTimeout(function() {
            this.el.scrollTop(this.el[0].scrollHeight);
        }.bind(this), 0);
    };

    /**
     * Hide the message panel
     */
    this.hide = function() {
        this.el.addClass("ui-helper-hidden");
    };

    /**
     * Show the message panel
     */
    this.show = function() {
        this.el.removeClass("ui-helper-hidden");
    };

    this.init();

}
