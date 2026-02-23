/**
 * jodit_base64_upload.js — Client-side defense against base64 images in Jodit editors.
 *
 * When users paste images from clipboard (Word, Google Docs, screenshots), the browser
 * inserts them as <img src="data:image/png;base64,..."> — multi-megabyte text blobs that
 * cause memory errors when saved to the database.
 *
 * This module intercepts base64 images via a MutationObserver (primary) and afterPaste
 * event (secondary), auto-uploads them to the server via the existing image upload
 * endpoint, and replaces the data: URI with the uploaded URL.
 *
 * Depends on: jQuery as $j, csrf_init.js (for csrf_token/refresh_csrf_cookie)
 *
 * Usage: After creating a Jodit instance, call:
 *   espHandleBase64Paste(editor);
 *
 * See: https://github.com/learning-unlimited/ESP-Website/issues/3612
 */
(function(global) {
    'use strict';

    var MAX_CONCURRENT = 2;
    var MAX_FILE_SIZE = 5 * 1024 * 1024;  // 5 MB decoded binary
    var UPLOAD_URL = '/admin/ajax_qsd_image_upload/';

    // Shared queue state across all editor instances on the page
    var activeUploads = 0;
    var uploadQueue = [];

    /**
     * Convert a base64 data URI to a File object.
     *
     * @param {string} dataUri - e.g. "data:image/png;base64,iVBOR..."
     * @param {string} filename - desired filename
     * @returns {File|null} File object, or null if conversion fails
     */
    function dataUriToFile(dataUri, filename) {
        try {
            var parts = dataUri.split(',');
            if (parts.length < 2) return null;

            var meta = parts[0];
            var mimeMatch = meta.match(/data:([^;]+)/);
            if (!mimeMatch) return null;

            var mime = mimeMatch[1];
            if (mime.indexOf('image/') !== 0) return null;

            var byteString = atob(parts[1]);
            var ab = new ArrayBuffer(byteString.length);
            var ia = new Uint8Array(ab);
            for (var i = 0; i < byteString.length; i++) {
                ia[i] = byteString.charCodeAt(i);
            }
            return new File([ab], filename, { type: mime });
        } catch (e) {
            return null;
        }
    }

    /**
     * Derive file extension from MIME type.
     */
    function extensionFromMime(mime) {
        var map = {
            'image/png': 'png',
            'image/jpeg': 'jpg',
            'image/gif': 'gif',
            'image/webp': 'webp',
            'image/bmp': 'bmp'
        };
        return map[mime] || 'png';
    }

    /**
     * Parse an error message from an XHR failure response.
     */
    function parseErrorMsg(xhr) {
        try {
            var resp = JSON.parse(xhr.responseText);
            if (resp.data && resp.data.messages) {
                return resp.data.messages.join('\n');
            }
        } catch (e) { /* ignore parse errors */ }

        if (xhr.status === 413) return 'Image too large for server';
        if (xhr.status === 401) return 'Not logged in — please log in and try again';
        if (xhr.status === 403) return 'Permission denied — admin access required';
        return 'Network error (status ' + xhr.status + ')';
    }

    /**
     * Remove a base64 image from the editor and show an error toast.
     */
    function handleFailure(editor, imgEl, msg) {
        if (imgEl.parentNode) {
            imgEl.parentNode.removeChild(imgEl);
        }
        editor.events.fire('errorMessage',
            'Image upload failed: ' + msg + '. Use the image button in the toolbar to upload.',
            'error', 5000);
    }

    /**
     * Process the next item(s) in the upload queue, up to MAX_CONCURRENT.
     */
    function processQueue() {
        while (activeUploads < MAX_CONCURRENT && uploadQueue.length > 0) {
            var task = uploadQueue.shift();
            doUpload(task.editor, task.img, task.file);
        }
    }

    /**
     * Upload a single file and replace the <img> src on success.
     */
    function doUpload(editor, imgEl, file) {
        activeUploads++;

        // Visual feedback: blur + reduced opacity while uploading
        imgEl.style.filter = 'blur(2px)';
        imgEl.style.opacity = '0.6';

        // Ensure CSRF token cookie is fresh (may have expired during long editing sessions)
        if (typeof refresh_csrf_cookie === 'function') {
            refresh_csrf_cookie();
        }

        var formData = new FormData();
        formData.append('files[0]', file, file.name);

        $j.ajax({
            url: UPLOAD_URL,
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            headers: { 'X-CSRFToken': csrf_token() },
            success: function(resp) {
                if (resp.success && resp.data && resp.data.files && resp.data.files.length > 0) {
                    imgEl.setAttribute('src', resp.data.files[0]);
                    imgEl.style.filter = '';
                    imgEl.style.opacity = '';
                    imgEl.removeAttribute('data-base64-uploading');
                    imgEl.removeAttribute('data-retried');
                } else {
                    var msgs = (resp.data && resp.data.messages) ? resp.data.messages.join('\n') : 'Unknown error';
                    handleFailure(editor, imgEl, msgs);
                }
            },
            error: function(xhr) {
                // One retry on server errors (5xx) — could be a transient issue
                if (xhr.status >= 500 && !imgEl.getAttribute('data-retried')) {
                    imgEl.setAttribute('data-retried', 'true');
                    uploadQueue.push({ editor: editor, img: imgEl, file: file });
                } else {
                    handleFailure(editor, imgEl, parseErrorMsg(xhr));
                }
            },
            complete: function() {
                activeUploads--;
                processQueue();
            }
        });
    }

    /**
     * Scan a DOM container for <img> elements with data: URIs and queue them
     * for upload. Skips images already being processed.
     */
    function scanAndUpload(editor, container) {
        var imgs = container.querySelectorAll('img[src^="data:"]');
        if (imgs.length === 0) return;

        for (var i = 0; i < imgs.length; i++) {
            var img = imgs[i];

            // Skip images already queued or being uploaded
            if (img.getAttribute('data-base64-uploading')) continue;
            img.setAttribute('data-base64-uploading', 'true');

            var src = img.getAttribute('src');

            // Extract MIME type
            var mimeMatch = src.match(/data:([^;,]+)/);
            var mime = mimeMatch ? mimeMatch[1] : 'image/png';
            var ext = extensionFromMime(mime);
            var filename = 'pasted-image-' + Date.now() + '-' + i + '.' + ext;

            // Convert data URI to File
            var file = dataUriToFile(src, filename);
            if (!file) {
                handleFailure(editor, img, 'Could not process pasted image data');
                continue;
            }

            // Client-side size check before uploading
            if (file.size > MAX_FILE_SIZE) {
                handleFailure(editor, img, 'Image exceeds the 5 MB size limit — please resize and try again');
                continue;
            }

            uploadQueue.push({ editor: editor, img: img, file: file });
        }

        processQueue();
    }

    /**
     * Attach the base64 paste handler to a Jodit editor instance.
     *
     * Uses two mechanisms:
     * 1. MutationObserver (primary) — catches base64 images from ANY source:
     *    paste, drag-drop, programmatic insertHTML, browser autofill, etc.
     * 2. afterPaste event (secondary) — fires immediately on paste for faster
     *    response on the most common case.
     *
     * @param {Jodit} editor - A Jodit editor instance
     */
    function espHandleBase64Paste(editor) {
        var editorArea = editor.editor;  // the contentEditable div

        // PRIMARY: MutationObserver watches for any new <img> nodes with data: URIs
        var observer = new MutationObserver(function(mutations) {
            var hasNewImages = false;
            for (var i = 0; i < mutations.length; i++) {
                var added = mutations[i].addedNodes;
                for (var j = 0; j < added.length; j++) {
                    var node = added[j];
                    if (node.nodeType !== 1) continue;  // skip text nodes

                    if (node.tagName === 'IMG' && (node.getAttribute('src') || '').indexOf('data:') === 0) {
                        hasNewImages = true;
                    } else if (node.querySelectorAll) {
                        var nested = node.querySelectorAll('img[src^="data:"]');
                        if (nested.length > 0) hasNewImages = true;
                    }
                }
            }
            if (hasNewImages) {
                setTimeout(function() { scanAndUpload(editor, editorArea); }, 50);
            }
        });
        observer.observe(editorArea, { childList: true, subtree: true });

        // SECONDARY: afterPaste for faster response on paste events
        editor.events.on('afterPaste', function() {
            setTimeout(function() { scanAndUpload(editor, editorArea); }, 50);
        });
    }

    // Export to global scope
    global.espHandleBase64Paste = espHandleBase64Paste;

})(window);
