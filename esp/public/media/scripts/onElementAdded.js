/**
 * Observes the DOM for elements matching a CSS selector and calls a callback
 * when they are added. Replaces the unmaintained jquery.initialize plugin
 * using the native MutationObserver API.
 *
 * @param {string} selector - CSS selector to match
 * @param {function} callback - Function called with each matching element as 'this'
 * @param {Element} [target=document] - Root element to observe
 * @returns {MutationObserver} The observer instance
 */
function onElementAdded(selector, callback, target) {
    var root = target || document;
    // Process any existing matching elements
    root.querySelectorAll(selector).forEach(function(el) {
        callback.call(el);
    });
    // Watch for new elements being added to the DOM
    var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) {
                    if (node.matches && node.matches(selector)) {
                        callback.call(node);
                    }
                    if (node.querySelectorAll) {
                        node.querySelectorAll(selector).forEach(function(el) {
                            callback.call(el);
                        });
                    }
                }
            });
        });
    });
    observer.observe(root, { childList: true, subtree: true });
    return observer;
}
