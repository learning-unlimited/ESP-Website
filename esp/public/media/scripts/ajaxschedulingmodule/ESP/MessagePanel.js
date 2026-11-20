/**
 * The panel that shows error and log messages to the user.
 *
 * @param el: The element to render into the panel
 * @param initialMessage: The message to go initially on the panel
 */
function MessagePanel(el, initialMessage) {
    this.el = el;

    this.showToast = function (msg, type) {
        var bgColor = "#333";
        if (type === "error") {
            bgColor = "#ef4444";
        } else if (type === "success") {
            bgColor = "#10b981";
        }

        var $toast = $j('<div>', { "class": 'scheduler-toast scheduler-toast-' + type })
            .text(msg)
            .css({
                position: 'fixed',
                top: '24px',
                bottom: 'auto',
                left: '50%',
                right: 'auto',
                transform: 'translateX(-50%) translateY(8px)',
                zIndex: 2147483647,
                backgroundColor: bgColor,
                color: '#fff',
                padding: '12px 16px',
                borderRadius: '8px',
                boxShadow: '0 8px 24px rgba(0, 0, 0, 0.2)',
                fontSize: '14px',
                fontWeight: '600',
                transition: 'opacity 0.25s ease, transform 0.25s ease',
                pointerEvents: 'none',
                opacity: 0
            });
        $j('body').append($toast);

        setTimeout(function () {
            $toast.css({
                opacity: 1,
                transform: 'translateX(-50%) translateY(0)',
            });
        }, 10);

        setTimeout(function () {
            $toast.css({
                opacity: 0,
                transform: 'translateX(-50%) translateY(8px)',
            });
            setTimeout(function () {
                $toast.remove();
            }, 250);
        }, 3000);
    };

    /**
     * Initialize the panel with the initial message
     */
    this.init = function () {
        if (initialMessage) {
            this.el.append(initialMessage);
        }
    };

    /**
     * Append a line to the message div in the form of a <p>.
     *
     * @param msg: The message to add
     */
    this.addMessage = function (msg, type) {
        if (!type && typeof msg === "string") {
            if (/^\s*Error:/i.test(msg)) {
                type = "error";
            } else if (/^\s*Success:/i.test(msg)) {
                type = "success";
            }
        }
        if (type) {
            this.showToast(msg, type);
        }
    };

    /**
     * Hide the message panel
     */
    this.hide = function () {
        this.el.addClass("ui-helper-hidden");
    };

    /**
     * Show the message panel
     */
    this.show = function () {
        this.el.removeClass("ui-helper-hidden");
    };

    this.init();

}
