// Calls callback (with `this` set to the element) once for every element
// matching selector that is inside target now or is added to it later.
// If target is omitted, the whole document is observed.
function initializeElements(selector, callback, target) {
    if (target === undefined) target = document.documentElement;
    var seen = new WeakSet();
    function init(el) {
        if (!seen.has(el)) {
            seen.add(el);
            callback.call(el);
        }
    }
    target.querySelectorAll(selector).forEach(init);
    new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            mutation.addedNodes.forEach(function (node) {
                if (!(node instanceof Element)) return;
                if (node.matches(selector)) init(node);
                node.querySelectorAll(selector).forEach(init);
            });
        });
    }).observe(target, { childList: true, subtree: true });
}
